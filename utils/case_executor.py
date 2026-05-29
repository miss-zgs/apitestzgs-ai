"""
用例执行引擎

提供通用的用例执行逻辑，所有测试文件都可以直接 import 使用。
支持：
    - ${变量名} 语法自动替换
    - extract 字段从响应中提取变量
    - base_url 字段指定独立域名
    - CSV 字段反序列化
    - 断言失败自动记录 Bug 到 BUGFIX.md
"""
import json
import logging
import traceback
from typing import List

import requests

from utils.context import resolve_variables, extract_and_save
from utils.assertion import assert_by_expect
from utils.bug_reporter import bug_handler

logger = logging.getLogger(__name__)


def execute_case(case: dict, http_client) -> requests.Response:
    """
    根据用例字典执行请求

    支持：
    1. ${变量名} 语法 — 自动从上下文中替换变量
    2. extract 字段 — 从响应中提取值存入上下文供后续用例使用
    3. base_url 字段 — 用例可指定独立的域名（如飞猪接口）

    :param case: 用例字典
    :param http_client: HttpClient 实例
    :return: 响应对象
    """
    # 输出当前执行的用例名称
    case_name = case.get("case_name", "未命名用例")
    logger.info("========== 执行用例: %s ==========", case_name)

    # 1. 变量替换：将用例中的 ${xxx} 替换为上下文中的实际值
    resolved = resolve_variables(case)

    method = resolved.get("method", "GET").upper()
    url = resolved.get("url", "")
    params = resolved.get("params")
    json_data = resolved.get("json")
    headers = resolved.get("headers")
    data = resolved.get("data")
    case_base_url = resolved.get("base_url")

    # 2. 如果用例指定了 base_url，拼接完整 URL
    if case_base_url:
        url = case_base_url.rstrip("/") + "/" + url.lstrip("/")

    kwargs = {}
    if headers:
        kwargs["headers"] = headers

    if method == "GET":
        response = http_client.get(url, params=params, **kwargs)
    elif method == "POST":
        response = http_client.post(url, data=data, json_data=json_data, **kwargs)
    elif method == "PUT":
        response = http_client.put(url, data=data, json_data=json_data, **kwargs)
    elif method == "DELETE":
        response = http_client.delete(url, **kwargs)
    elif method == "PATCH":
        response = http_client.patch(url, data=data, json_data=json_data, **kwargs)
    else:
        raise ValueError(f"不支持的请求方法: {method}")

    # 3. 提取变量：如果用例中有 extract 字段，从响应中提取值存入上下文
    extract_rules = resolved.get("extract")
    if extract_rules:
        try:
            response_json = response.json()
            extract_and_save(response_json, extract_rules)
        except ValueError:
            pass

    return response


def execute_chain(cases: List[dict], http_client, case_file: str = ""):
    """
    串行执行多个用例（接口依赖编排）

    按顺序执行，每个用例执行完后自动提取变量，后续用例自动引用。
    断言失败时自动记录 Bug 到 BUGFIX.md。

    :param cases: 用例列表
    :param http_client: HttpClient 实例
    :param case_file: 用例数据文件名（用于 Bug 报告定位）
    """
    total = len(cases)
    for index, case in enumerate(cases, start=1):
        case_name = case.get("case_name", "未命名用例")
        response = execute_case(case, http_client)

        expect = case.get("expect")
        if expect:
            try:
                assert_by_expect(response, resolve_variables(expect))
            except (AssertionError, Exception) as exc:
                # 收集请求信息
                resolved = resolve_variables(case)
                request_info = {
                    "method": resolved.get("method", "GET").upper(),
                    "url": _build_full_url(resolved),
                    "headers": resolved.get("headers"),
                    "body": resolved.get("json") or resolved.get("data"),
                }

                # 收集响应信息
                response_info = _build_response_info(response)

                # 自动记录 Bug
                bug_handler(
                    bug_title=f"{case_name} - {str(exc)[:80]}",
                    severity="高",
                    case_name=case_name,
                    case_file=case_file,
                    step_info=f"步骤 {index}/{total}",
                    request_info=request_info,
                    response_info=response_info,
                    error_message=str(exc),
                    traceback_str=traceback.format_exc(),
                )

                # 继续抛出异常，让 pytest 标记为 FAILED
                raise


def parse_csv_case(case: dict) -> dict:
    """
    CSV 用例的字符串字段反序列化为 dict

    CSV 读出来的 json/expect/params/headers 字段是字符串，需要 json.loads 转为 dict。

    :param case: 原始用例字典
    :return: 反序列化后的用例字典
    """
    parsed = dict(case)
    for field in ("json", "expect", "params", "headers"):
        value = parsed.get(field)
        if isinstance(value, str) and value.strip():
            try:
                parsed[field] = json.loads(value)
            except json.JSONDecodeError:
                pass
    return parsed


# ==================== 内部辅助方法 ====================


def _build_full_url(resolved_case: dict) -> str:
    """根据用例构建完整 URL"""
    url = resolved_case.get("url", "")
    case_base_url = resolved_case.get("base_url")
    if case_base_url:
        url = case_base_url.rstrip("/") + "/" + url.lstrip("/")
    return url


def _build_response_info(response: requests.Response) -> dict:
    """从 Response 对象提取响应信息"""
    info = {
        "status_code": response.status_code,
        "elapsed": round(response.elapsed.total_seconds(), 3),
    }
    try:
        info["body"] = response.json()
    except ValueError:
        info["body"] = response.text[:500]
    return info
