"""
断言工具

将 utils/assertion.py 封装为 LangChain Tool，供 Agent 调用。
提供状态码校验、jsonpath 字段校验、包含/类型/非空断言等能力。
所有 dict 类型参数改为 JSON 字符串传递，避免 Claude API schema 不兼容。
"""
import json
import logging

from jsonpath_ng.ext import parse as jsonpath_parse
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def _parse_response_body(response_body_json: str) -> dict:
    """将响应体 JSON 字符串解析为 dict"""
    try:
        result = json.loads(response_body_json)
        return result if isinstance(result, dict) else {"_raw": result}
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError(f"响应体 JSON 解析失败: {exc}")


@tool
def check_status_code(actual_status_code: int, expected_status_code: int) -> str:
    """校验 HTTP 响应状态码是否符合预期。

    Args:
        actual_status_code: 实际收到的 HTTP 状态码
        expected_status_code: 期望的 HTTP 状态码

    Returns:
        校验结果（通过或失败详情）
    """
    if actual_status_code == expected_status_code:
        return f"✅ 状态码校验通过: {actual_status_code} == {expected_status_code}"
    else:
        return f"❌ 状态码校验失败: 期望 {expected_status_code}, 实际 {actual_status_code}"


@tool
def check_json_field(response_body_json: str, json_path: str, expected_value: str) -> str:
    """通过 JSONPath 表达式提取响应体中的字段，并校验其值是否符合预期。

    Args:
        response_body_json: HTTP 响应体的 JSON 字符串，如 {"code": 0, "data": {"name": "test"}}
        json_path: JSONPath 表达式，如 $.code、$.data.name、$.data.list[0].id
        expected_value: 期望的字段值（字符串形式，数字也传字符串如 "200"、"0"）

    Returns:
        校验结果（通过或失败详情）
    """
    try:
        response_body = _parse_response_body(response_body_json)
        matches = jsonpath_parse(json_path).find(response_body)
        if not matches:
            return f"❌ JSONPath '{json_path}' 在响应中未匹配到任何值\n响应体: {response_body_json[:500]}"

        actual_value = matches[0].value

        # 智能比较：尝试将 expected_value 转为对应类型
        expected_converted = _smart_convert(expected_value)

        if actual_value == expected_converted:
            return f"✅ 字段校验通过: {json_path} = {actual_value!r}"
        else:
            return f"❌ 字段校验失败: {json_path} 期望 {expected_converted!r}, 实际 {actual_value!r}"

    except ValueError as exc:
        return f"❌ {exc}"
    except Exception as exc:
        return f"❌ JSONPath 解析错误: {exc}"


@tool
def check_json_contains(response_body_json: str, json_path: str, keyword: str) -> str:
    """校验 JSONPath 提取的字段值是否包含指定关键词。

    Args:
        response_body_json: HTTP 响应体的 JSON 字符串
        json_path: JSONPath 表达式
        keyword: 期望包含的关键词

    Returns:
        校验结果
    """
    try:
        response_body = _parse_response_body(response_body_json)
        matches = jsonpath_parse(json_path).find(response_body)
        if not matches:
            return f"❌ JSONPath '{json_path}' 未匹配到值"

        actual_value = str(matches[0].value)
        if keyword in actual_value:
            return f"✅ 包含校验通过: {json_path} 的值包含 '{keyword}'"
        else:
            return f"❌ 包含校验失败: {json_path} 的值 '{actual_value}' 不包含 '{keyword}'"

    except ValueError as exc:
        return f"❌ {exc}"
    except Exception as exc:
        return f"❌ 校验错误: {exc}"


@tool
def check_json_not_empty(response_body_json: str, json_path: str) -> str:
    """校验 JSONPath 提取的字段值不为空（非 None、非空字符串、非空列表）。

    Args:
        response_body_json: HTTP 响应体的 JSON 字符串
        json_path: JSONPath 表达式

    Returns:
        校验结果
    """
    try:
        response_body = _parse_response_body(response_body_json)
        matches = jsonpath_parse(json_path).find(response_body)
        if not matches:
            return f"❌ JSONPath '{json_path}' 未匹配到值"

        actual_value = matches[0].value
        if actual_value:
            return f"✅ 非空校验通过: {json_path} = {actual_value!r}"
        else:
            return f"❌ 非空校验失败: {json_path} 的值为空: {actual_value!r}"

    except ValueError as exc:
        return f"❌ {exc}"
    except Exception as exc:
        return f"❌ 校验错误: {exc}"


@tool
def extract_json_value(response_body_json: str, json_path: str) -> str:
    """从响应体中通过 JSONPath 提取字段值（不做断言，仅提取返回）。

    常用于提取 token、id 等值供后续请求使用。

    Args:
        response_body_json: HTTP 响应体的 JSON 字符串
        json_path: JSONPath 表达式

    Returns:
        提取到的值（字符串形式）
    """
    try:
        response_body = _parse_response_body(response_body_json)
        matches = jsonpath_parse(json_path).find(response_body)
        if not matches:
            return f"未匹配到值: JSONPath '{json_path}' 无结果"

        value = matches[0].value
        return f"提取成功: {json_path} = {json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else repr(value)}"

    except ValueError as exc:
        return f"❌ {exc}"
    except Exception as exc:
        return f"提取失败: {exc}"


def _smart_convert(value_str: str):
    """
    智能类型转换：将字符串尝试转为 int/float/bool/None

    用于 check_json_field 中将期望值字符串和实际值做比较。
    """
    if value_str.lower() == "null" or value_str.lower() == "none":
        return None
    if value_str.lower() == "true":
        return True
    if value_str.lower() == "false":
        return False
    try:
        return int(value_str)
    except ValueError:
        pass
    try:
        return float(value_str)
    except ValueError:
        pass
    # 尝试解析为 JSON（支持 list/dict）
    try:
        return json.loads(value_str)
    except (json.JSONDecodeError, TypeError):
        pass
    return value_str
