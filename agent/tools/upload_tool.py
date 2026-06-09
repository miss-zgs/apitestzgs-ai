"""
文件上传工具

支持 Agent 将 data/ 目录下的文件通过 multipart/form-data 上传到被测接口。
用户先把文件放到 data/ 目录，然后告诉 Agent 上传到哪个接口。
"""
import json
import logging
import mimetypes
import os

from langchain_core.tools import tool

from utils.http_client import HttpClient
from agent.config import MAX_RESPONSE_LENGTH
from config.settings import get_project_root

logger = logging.getLogger(__name__)

# 允许上传的文件扩展名白名单
ALLOWED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg",  # 图片
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",  # 文档
    ".txt", ".csv", ".json", ".yaml", ".yml", ".xml",  # 文本
    ".zip", ".tar", ".gz", ".rar",  # 压缩包
    ".mp4", ".mp3", ".wav",  # 音视频
}

# 最大文件大小：50MB
MAX_FILE_SIZE = 50 * 1024 * 1024


@tool
def upload_file(
    url: str,
    file_path: str,
    file_field: str = "file",
    form_data: str = "",
    headers: str = "",
    base_url: str = "",
) -> str:
    """将 data/ 目录下的文件通过 multipart/form-data 上传到指定接口。

    用户需先将文件放到项目的 data/ 目录下，然后告诉你文件名和目标接口。

    Args:
        url: 上传接口 URL，可以是完整 URL 或相对路径（自动拼接 base_url）
        file_path: 文件路径，相对于 data/ 目录，如 "avatar.png" 或 "images/test.jpg"
        file_field: 接口接收文件的字段名，默认 "file"。有些接口可能用 "image"、"attachment" 等
        form_data: 随文件一起提交的表单字段，JSON 字符串格式如 {"name": "测试图片", "type": "avatar"}。不需要时传空字符串
        headers: 请求头，JSON 字符串格式。不需要时传空字符串
        base_url: 指定独立的 base_url（覆盖全局配置）。不需要时传空字符串

    Returns:
        上传结果，包含状态码和响应体
    """
    # 构建完整文件路径（限制在 data/ 目录下）
    data_dir = os.path.join(get_project_root(), "data")
    full_path = os.path.normpath(os.path.join(data_dir, file_path))

    # 安全检查：防止路径穿越
    if not full_path.startswith(data_dir):
        return f"❌ 安全限制: 只允许上传 data/ 目录下的文件，禁止路径穿越"

    # 文件存在性检查
    if not os.path.isfile(full_path):
        available_files = _list_uploadable_files(data_dir)
        hint = f"\ndata/ 目录下可用的文件:\n{available_files}" if available_files else "\ndata/ 目录下暂无文件"
        return f"❌ 文件不存在: data/{file_path}{hint}"

    # 扩展名检查
    _, extension = os.path.splitext(full_path)
    if extension.lower() not in ALLOWED_EXTENSIONS:
        return f"❌ 不支持的文件类型: {extension}，允许的类型: {', '.join(sorted(ALLOWED_EXTENSIONS))}"

    # 文件大小检查
    file_size = os.path.getsize(full_path)
    if file_size > MAX_FILE_SIZE:
        return f"❌ 文件过大: {file_size / 1024 / 1024:.1f}MB，最大允许 {MAX_FILE_SIZE / 1024 / 1024:.0f}MB"

    if file_size == 0:
        return f"❌ 文件为空: data/{file_path}"

    # 解析表单字段和请求头
    form_dict = _parse_json_str(form_data)
    headers_dict = _parse_json_str(headers)

    # 获取 MIME 类型
    mime_type = mimetypes.guess_type(full_path)[0] or "application/octet-stream"
    file_name = os.path.basename(full_path)

    try:
        client = HttpClient(base_url=base_url) if base_url else HttpClient()

        with open(full_path, "rb") as file_obj:
            files = {file_field: (file_name, file_obj, mime_type)}
            kwargs = {}
            if headers_dict:
                kwargs["headers"] = headers_dict

            response = client.upload(url, files=files, data=form_dict or None, **kwargs)

        # 格式化响应
        result_parts = [
            f"✅ 文件上传完成",
            f"文件: data/{file_path} ({file_size / 1024:.1f}KB, {mime_type})",
            f"状态码: {response.status_code}",
            f"URL: {response.url}",
            f"耗时: {response.elapsed.total_seconds():.3f}s",
        ]

        try:
            body = response.json()
            body_str = json.dumps(body, ensure_ascii=False, indent=2)
            if len(body_str) > MAX_RESPONSE_LENGTH:
                body_str = body_str[:MAX_RESPONSE_LENGTH] + "\n... [响应已截断]"
            result_parts.append(f"响应体(JSON):\n{body_str}")
        except ValueError:
            text = response.text[:MAX_RESPONSE_LENGTH]
            result_parts.append(f"响应体(文本):\n{text}")

        return "\n".join(result_parts)

    except Exception as exc:
        logger.error("文件上传失败: %s", exc)
        return f"❌ 上传失败: {type(exc).__name__}: {str(exc)}"


@tool
def list_uploadable_files() -> str:
    """列出 data/ 目录下所有可上传的文件。

    查看用户放在 data/ 目录下的文件列表，包含文件名、大小和类型。

    Returns:
        文件列表，包含文件名、大小和类型
    """
    data_dir = os.path.join(get_project_root(), "data")
    result = _list_uploadable_files(data_dir)
    if not result:
        return "data/ 目录下暂无可上传的文件。请先将文件放到 data/ 目录中。"
    return f"data/ 目录下的文件:\n{result}"


def _list_uploadable_files(data_dir: str) -> str:
    """列出目录下所有可上传的文件"""
    if not os.path.isdir(data_dir):
        return ""

    files = []
    for root, _, filenames in os.walk(data_dir):
        for filename in sorted(filenames):
            if filename.startswith("."):
                continue
            filepath = os.path.join(root, filename)
            relative = os.path.relpath(filepath, data_dir)
            size = os.path.getsize(filepath)
            _, ext = os.path.splitext(filename)
            if size > 0:
                size_str = f"{size / 1024:.1f}KB" if size < 1024 * 1024 else f"{size / 1024 / 1024:.1f}MB"
                files.append(f"  - {relative} ({size_str}, {ext})")

    return "\n".join(files) if files else ""


def _parse_json_str(json_str: str) -> dict:
    """将 JSON 字符串解析为 dict"""
    if not json_str or json_str.strip() in ("", "{}", "null"):
        return {}
    try:
        result = json.loads(json_str)
        return result if isinstance(result, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}
