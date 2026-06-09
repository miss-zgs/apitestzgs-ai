"""
文件读取工具

提供文件读取能力，让 Agent 能查看配置文件、日志等。
仅支持只读操作，不允许写入。
"""
import logging
import os

from langchain_core.tools import tool

from config.settings import get_project_root

logger = logging.getLogger(__name__)

# 允许读取的目录白名单（相对于项目根目录）
_READABLE_DIRS = ["config", "data", "logs", "docs"]

# 允许读取的根目录文件
_READABLE_ROOT_FILES = [
    "README.md", "CHANGELOG.md", "TODO.md",
    "requirements.txt",
]


@tool
def read_project_file(file_path: str) -> str:
    """读取项目中的文件内容（只读）。

    仅允许读取 config/、data/、logs/、docs/ 目录下的文件，
    以及项目根目录的 README.md、CHANGELOG.md 等文档文件。
    出于安全考虑，不允许读取 utils/、agent/ 等代码文件。

    Args:
        file_path: 文件相对路径，如 "config/config.yaml"、"data/test_demo.yaml"、"README.md"

    Returns:
        文件内容或错误信息
    """
    try:
        project_root = get_project_root()

        # 安全检查：禁止路径穿越
        if ".." in file_path:
            return "❌ 不允许使用 '..' 路径穿越"

        # 构建绝对路径
        abs_path = os.path.join(project_root, file_path)

        # 安全检查：是否在允许的范围内
        if not _is_allowed_path(file_path):
            return f"❌ 无权读取该文件: {file_path}\n允许读取的目录: {', '.join(_READABLE_DIRS)}\n允许读取的根目录文件: {', '.join(_READABLE_ROOT_FILES)}"

        if not os.path.isfile(abs_path):
            return f"❌ 文件不存在: {file_path}"

        # 读取文件（限制大小）
        file_size = os.path.getsize(abs_path)
        if file_size > 50000:
            return f"❌ 文件过大 ({file_size} bytes)，超过 50KB 限制"

        with open(abs_path, "r", encoding="utf-8") as file:
            content = file.read()

        # 截断过长内容
        if len(content) > 5000:
            content = content[:5000] + f"\n\n... [文件已截断，共 {len(content)} 字符]"

        return f"📄 文件: {file_path}\n{'=' * 40}\n{content}"

    except UnicodeDecodeError:
        return f"❌ 文件不是文本格式，无法读取: {file_path}"
    except Exception as exc:
        return f"❌ 读取失败: {exc}"


def _is_allowed_path(file_path: str) -> bool:
    """检查文件路径是否在允许读取的范围内"""
    # 根目录文件白名单
    if file_path in _READABLE_ROOT_FILES:
        return True

    # 目录白名单
    for allowed_dir in _READABLE_DIRS:
        if file_path.startswith(f"{allowed_dir}/"):
            return True

    return False
