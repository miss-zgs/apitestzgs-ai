"""
HTTP 请求工具

将 utils/http_client.py 封装为 LangChain Tool，供 Agent 调用。
所有 dict 类型参数改为 JSON 字符串传递，避免 Claude API schema 不兼容。
"""
import json
import logging

from langchain_core.tools import tool

from utils.http_client import HttpClient
from agent.config import MAX_RESPONSE_LENGTH, MAX_REQUESTS_PER_TASK

logger = logging.getLogger(__name__)

# 模块级请求计数器（每次 Agent 任务重置）
_request_counter: int = 0


def reset_request_counter():
    """重置请求计数器（每次新任务开始时调用）"""
    global _request_counter
    _request_counter = 0


def get_request_count() -> int:
    """获取当前任务已发送的请求数"""
    return _request_counter


def _parse_json_str(json_str: str) -> dict:
    """将 JSON 字符串解析为 dict，空字符串返回空 dict"""
    if not json_str or json_str.strip() in ("", "{}", "null"):
        return {}
    try:
        result = json.loads(json_str)
        return result if isinstance(result, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


@tool
def send_http_request(
    method: str,
    url: str,
    headers: str = "",
    params: str = "",
    json_body: str = "",
    base_url: str = "",
) -> str:
    """向指定 URL 发送 HTTP 请求。

    支持 GET/POST/PUT/DELETE/PATCH 方法。返回 HTTP 状态码和响应体。
    如果请求失败会自动重试。

    Args:
        method: HTTP 方法，必须是 GET/POST/PUT/DELETE/PATCH 之一
        url: 请求 URL，可以是完整 URL（以 http 开头）或相对路径（会自动拼接当前环境的 base_url）
        headers: 请求头，JSON 字符串格式如 {"Authorization": "Bearer xxx"}。不需要时传空字符串
        params: URL 查询参数，JSON 字符串格式如 {"page": 1, "size": 10}。不需要时传空字符串
        json_body: JSON 请求体，仅 POST/PUT/PATCH 时使用，JSON 字符串格式。不需要时传空字符串
        base_url: 指定独立的 base_url（覆盖全局配置）。不需要时传空字符串

    Returns:
        包含状态码和响应体的格式化字符串
    """
    global _request_counter

    # 安全检查：请求数限制
    if _request_counter >= MAX_REQUESTS_PER_TASK:
        return f"❌ 已达到单次任务最大请求数限制（{MAX_REQUESTS_PER_TASK}次），请结束当前任务或确认是否继续。"

    method = method.upper()
    if method not in ("GET", "POST", "PUT", "DELETE", "PATCH"):
        return f"❌ 不支持的 HTTP 方法: {method}，请使用 GET/POST/PUT/DELETE/PATCH"

    # 解析 JSON 字符串参数
    headers_dict = _parse_json_str(headers)
    params_dict = _parse_json_str(params)
    json_body_dict = _parse_json_str(json_body)

    try:
        client = HttpClient(base_url=base_url) if base_url else HttpClient()

        kwargs = {}
        if headers_dict:
            kwargs["headers"] = headers_dict

        if method == "GET":
            response = client.get(url, params=params_dict or None, **kwargs)
        elif method == "POST":
            response = client.post(url, json_data=json_body_dict or None, **kwargs)
        elif method == "PUT":
            response = client.put(url, json_data=json_body_dict or None, **kwargs)
        elif method == "DELETE":
            response = client.delete(url, **kwargs)
        elif method == "PATCH":
            response = client.patch(url, json_data=json_body_dict or None, **kwargs)

        _request_counter += 1

        # 格式化响应
        result_parts = [
            f"✅ 请求成功",
            f"状态码: {response.status_code}",
            f"URL: {response.url}",
            f"耗时: {response.elapsed.total_seconds():.3f}s",
        ]

        # 响应体处理（截断过长内容）
        try:
            body = response.json()
            body_str = json.dumps(body, ensure_ascii=False, indent=2)
            if len(body_str) > MAX_RESPONSE_LENGTH:
                body_str = body_str[:MAX_RESPONSE_LENGTH] + "\n... [响应已截断]"
            result_parts.append(f"响应体(JSON):\n{body_str}")
        except ValueError:
            text = response.text[:MAX_RESPONSE_LENGTH]
            if len(response.text) > MAX_RESPONSE_LENGTH:
                text += "\n... [响应已截断]"
            result_parts.append(f"响应体(文本):\n{text}")

        return "\n".join(result_parts)

    except Exception as exc:
        logger.error("HTTP 请求失败: %s", exc)
        return f"❌ 请求失败: {type(exc).__name__}: {str(exc)}"
