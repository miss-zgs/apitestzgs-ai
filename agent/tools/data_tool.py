"""
数据加载工具

将 utils/data_loader.py 封装为 LangChain Tool，供 Agent 调用。
支持加载 YAML/JSON/CSV/Excel 格式的测试用例文件。
"""
import json
import logging
import os

from langchain_core.tools import tool

from config.settings import get_project_root
from utils.data_loader import load_test_data

logger = logging.getLogger(__name__)


@tool
def load_test_cases(file_path: str) -> str:
    """加载测试用例数据文件，支持 YAML/JSON/CSV/Excel 格式。

    文件路径可以是相对路径（相对于项目 data/ 目录）或绝对路径。
    返回用例数据的 JSON 格式字符串。

    Args:
        file_path: 用例数据文件路径。
                   相对路径示例: "test_demo.yaml"（自动在 data/ 目录下查找）
                   绝对路径示例: "/path/to/test_cases.yaml"

    Returns:
        用例数据的 JSON 字符串（列表格式），或错误信息
    """
    try:
        # 如果是相对路径，拼接 data/ 目录
        if not os.path.isabs(file_path):
            project_root = get_project_root()
            file_path = os.path.join(project_root, "data", file_path)

        cases = load_test_data(file_path)

        # 格式化输出
        result_parts = [f"✅ 成功加载 {len(cases)} 条用例 (文件: {os.path.basename(file_path)})"]
        result_parts.append("")

        for index, case in enumerate(cases, start=1):
            case_name = case.get("case_name", "未命名")
            method = case.get("method", "GET").upper()
            url = case.get("url", "")
            result_parts.append(f"  [{index}] {case_name} ({method} {url})")

        result_parts.append("")
        result_parts.append("完整数据:")
        cases_json = json.dumps(cases, ensure_ascii=False, indent=2)
        # 截断过长内容
        if len(cases_json) > 5000:
            cases_json = cases_json[:5000] + "\n... [数据已截断]"
        result_parts.append(cases_json)

        return "\n".join(result_parts)

    except FileNotFoundError as exc:
        return f"❌ 文件不存在: {exc}"
    except Exception as exc:
        logger.error("加载测试数据失败: %s", exc)
        return f"❌ 加载失败: {type(exc).__name__}: {exc}"


@tool
def list_test_data_files() -> str:
    """列出 data/ 目录下所有可用的测试数据文件。

    Returns:
        文件列表，包含文件名和大小信息
    """
    try:
        data_dir = os.path.join(get_project_root(), "data")
        if not os.path.isdir(data_dir):
            return "❌ data/ 目录不存在"

        supported_extensions = (".yaml", ".yml", ".json", ".csv", ".xlsx", ".xls")
        files = []

        for filename in sorted(os.listdir(data_dir)):
            if filename.startswith("."):
                continue
            ext = os.path.splitext(filename)[1].lower()
            if ext in supported_extensions:
                filepath = os.path.join(data_dir, filename)
                size = os.path.getsize(filepath)
                files.append(f"  - {filename} ({size} bytes)")

        if not files:
            return "data/ 目录下没有支持格式的测试数据文件"

        return f"📁 data/ 目录下共 {len(files)} 个数据文件:\n" + "\n".join(files)

    except Exception as exc:
        return f"❌ 列出文件失败: {exc}"
