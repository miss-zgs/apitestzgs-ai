"""
Bug 报告工具

统一的 Bug 处理方法，通过配置文件中的 bug.mode 控制功能模式：
    - bug.mode = "report": 记录 Bug 模式
    - bug.mode = "verify": 验证 Bug 模式

功能开关从 config/config.yaml 读取：
    bug:
      mode: "report"        # Bug 模式（report=记录 Bug, verify=验证 Bug）

使用方式：
    from utils.bug_reporter import bug_handler

    # 记录 Bug（当 bug.mode = "report" 时）
    bug_handler(bug_title="xxx", severity="高", ...)

    # 验证 Bug 修复（当 bug.mode = "verify" 时）
    result = bug_handler(bug_id="BUG-001")
"""
import json
import logging
import os
import platform
import re
import sys
import traceback
from datetime import datetime
from typing import Optional, Union

from config.settings import get_project_root, get_bug_mode

logger = logging.getLogger(__name__)

# Bug 记录文件路径
_BUGFIX_PATH = os.path.join(get_project_root(), "BUGFIX.md")

# Bug 模式（从配置文件读取）
_BUG_MODE = get_bug_mode()

# 需要脱敏的 Header 关键词（不区分大小写）
_SENSITIVE_KEYS = {"secret", "password", "token", "authorization", "cookie"}


def bug_handler(
    bug_id: str = "",
    bug_title: str = "",
    severity: str = "高",
    case_name: str = "",
    case_file: str = "",
    step_info: str = "",
    request_info: Optional[dict] = None,
    response_info: Optional[dict] = None,
    error_message: str = "",
    traceback_str: str = "",
    request_id: str = "",
    root_cause: str = "待分析",
    run_command: str = "",
    auto_update: bool = True,
    force: bool = False,
) -> Union[dict, None]:
    """
    统一的 Bug 处理方法

    根据配置文件中的 bug.mode 自动选择功能模式：
    - bug.mode = "report": 记录 Bug
    - bug.mode = "verify": 验证 Bug 修复

    调用方式始终相同，只需修改配置文件中的 bug.mode 即可切换功能：
    
    ```python
    from utils.bug_reporter import bug_handler
    
    # 无论 bug.mode 是什么，调用方式都一样
    bug_handler(bug_id="BUG-001", bug_title="xxx", ...)
    ```

    :param bug_id: Bug 编号（验证模式需要）
    :param bug_title: Bug 标题（记录模式需要）
    :param severity: 严重程度（高/中/低）
    :param case_name: 用例名称
    :param case_file: 用例数据文件
    :param step_info: 步骤信息
    :param request_info: 请求信息
    :param response_info: 响应信息
    :param error_message: 报错信息
    :param traceback_str: 完整堆栈
    :param request_id: 请求唯一 Key
    :param root_cause: 原因分析
    :param run_command: 复现命令
    :param auto_update: 是否自动更新 BUGFIX.md
    :param force: 强制操作（忽略开关配置）
    :return: 操作结果
    """
    # 根据配置文件中的模式自动选择功能
    if _BUG_MODE == "report":
        return _report_bug(
            bug_title=bug_title,
            severity=severity,
            case_name=case_name,
            case_file=case_file,
            step_info=step_info,
            request_info=request_info,
            response_info=response_info,
            error_message=error_message,
            traceback_str=traceback_str,
            request_id=request_id,
            root_cause=root_cause,
            run_command=run_command,
            force=force,
        )
    elif _BUG_MODE == "verify":
        return _verify_bug_fix(
            bug_id=bug_id,
            auto_update=auto_update,
            force=force,
        )
    else:
        logger.error("❌ 未知的 Bug 模式: %s", _BUG_MODE)
        return {"success": False, "error": f"未知的 Bug 模式: {_BUG_MODE}"}


def _report_bug(
    bug_title: str,
    severity: str = "高",
    case_name: str = "",
    case_file: str = "",
    step_info: str = "",
    request_info: Optional[dict] = None,
    response_info: Optional[dict] = None,
    error_message: str = "",
    traceback_str: str = "",
    request_id: str = "",
    root_cause: str = "待分析",
    run_command: str = "",
    force: bool = False,
) -> dict:
    """
    记录一个 Bug 到 BUGFIX.md
    """
    # 检查 Bug 模式开关
    if _BUG_MODE != "report" and not force:
        logger.debug("🚫 Bug 模式为 %s，跳过记录: %s", _BUG_MODE, bug_title)
        return {"success": False, "error": f"Bug 模式为 {_BUG_MODE}，无法记录 Bug"}

    bug_id = _next_bug_id()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    severity_icon = {"高": "🔴", "中": "🟡", "低": "🟢"}.get(severity, "⚪")

    # 自动捕获堆栈（如果调用方没传）
    if not traceback_str:
        traceback_str = traceback.format_exc()
        if traceback_str == "NoneType: None\n":
            traceback_str = ""

    # 收集环境信息
    env_info = _collect_env_info()

    # 收集上下文变量快照
    context_snapshot = _collect_context_snapshot()

    # 构建报告内容
    lines = []
    lines.append(f"## BUG-{bug_id:03d}：{bug_title}\n")
    lines.append(f"- **发现时间**：{now}")
    lines.append(f"- **严重程度**：{severity_icon} {severity}")
    lines.append(f"- **状态**：❌ 待修复")
    if request_id:
        lines.append(f"- **请求唯一 Key**：{request_id}")
    lines.append("")

    # 报错位置
    lines.append("### 报错位置")
    if case_name:
        lines.append(f"- **用例名称**：{case_name}")
    if case_file:
        file_desc = case_file
        if step_info:
            file_desc += f"（{step_info}）"
        lines.append(f"- **用例文件**：{file_desc}")
    if traceback_str:
        trigger_location = _extract_trigger_location(traceback_str)
        if trigger_location:
            lines.append(f"- **触发位置**：{trigger_location}")
    lines.append("")

    # 环境信息
    lines.append("### 环境信息")
    for key, value in env_info.items():
        lines.append(f"- **{key}**：{value}")
    lines.append("")

    # 请求信息
    if request_info:
        lines.append("### 请求信息")
        lines.append(f"- **Method**：{request_info.get('method', 'N/A')}")
        lines.append(f"- **URL**：{request_info.get('url', 'N/A')}")
        headers = request_info.get("headers")
        if headers:
            lines.append(f"- **Headers**：")
            lines.append("  ```json")
            lines.append(f"  {json.dumps(_mask_sensitive(headers), ensure_ascii=False)}")
            lines.append("  ```")
        body = request_info.get("body")
        if body:
            lines.append(f"- **Body**：")
            lines.append("  ```json")
            lines.append(f"  {_format_json(body)}")
            lines.append("  ```")
        lines.append("")

    # 响应信息
    if response_info:
        lines.append("### 响应信息")
        lines.append(f"- **Status Code**：{response_info.get('status_code', 'N/A')}")
        elapsed = response_info.get("elapsed")
        if elapsed is not None:
            lines.append(f"- **耗时**：{elapsed}s")
        resp_body = response_info.get("body")
        if resp_body:
            lines.append(f"- **Response Body**：")
            lines.append("  ```json")
            lines.append(f"  {_format_json(resp_body)}")
            lines.append("  ```")
        lines.append("")

    # 报错信息
    if error_message:
        lines.append("### 报错信息")
        lines.append("```")
        lines.append(error_message.strip())
        lines.append("```")
        lines.append("")

    # 完整堆栈
    if traceback_str:
        lines.append("### 完整堆栈")
        lines.append("```")
        lines.append(traceback_str.strip())
        lines.append("```")
        lines.append("")

    # 上下文变量快照
    if context_snapshot:
        lines.append("### 上下文变量快照")
        lines.append("```json")
        lines.append(json.dumps(context_snapshot, ensure_ascii=False, indent=2))
        lines.append("```")
        lines.append("")

    # 原因分析
    lines.append("### 原因分析")
    lines.append(root_cause)
    lines.append("")

    # 复现步骤
    lines.append("### 复现步骤")
    if run_command:
        lines.append(f"```bash\n{run_command}\n```")
    else:
        lines.append("```bash\npython3 -m pytest testcases/ -v\n```")
    lines.append("")
    lines.append("---\n")

    report_content = "\n".join(lines)

    # 写入文件
    _append_to_bugfix(report_content)

    logger.warning("🐛 已记录 BUG-%03d: %s → %s", bug_id, bug_title, _BUGFIX_PATH)

    return {"success": True, "bug_id": f"BUG-{bug_id:03d}"}


def _verify_bug_fix(bug_id: str, auto_update: bool = True, force: bool = False) -> dict:
    """
    验证指定 Bug 是否已修复
    """
    # 检查 Bug 模式开关
    if _BUG_MODE != "verify" and not force:
        logger.debug("🚫 Bug 模式为 %s，跳过验证: %s", _BUG_MODE, bug_id)
        return {"success": False, "error": f"Bug 模式为 {_BUG_MODE}，无法验证 Bug"}

    bug_info = get_bug_info(bug_id)
    if not bug_info:
        return {"success": False, "error": f"Bug {bug_id} 不存在"}

    # 如果 Bug 已修复，无需验证
    if "已修复" in bug_info.get("status", ""):
        return {"success": True, "message": f"Bug {bug_id} 已修复，无需验证"}

    # 获取用例文件
    case_file = bug_info.get("case_file", "")
    if not case_file:
        return {"success": False, "error": f"Bug {bug_id} 没有用例文件信息"}

    # 运行测试用例
    result = _run_test_case(case_file)

    # 更新 Bug 状态
    if auto_update and result["success"]:
        update_bug_status(bug_id, "已修复")

    return result


# ==================== 辅助方法 ====================


def _next_bug_id() -> int:
    """读取 BUGFIX.md 中已有的最大 Bug 编号，返回下一个编号"""
    if not os.path.isfile(_BUGFIX_PATH):
        return 1

    max_id = 0
    with open(_BUGFIX_PATH, "r", encoding="utf-8") as file:
        for line in file:
            match = re.match(r"## BUG-(\d+)", line)
            if match:
                bug_num = int(match.group(1))
                if bug_num > max_id:
                    max_id = bug_num
    return max_id + 1


def _collect_env_info() -> dict:
    """收集运行环境信息"""
    from config.settings import get_current_env, get_base_url

    return {
        "运行环境": get_current_env(),
        "Base URL": get_base_url(),
        "Python 版本": sys.version.split()[0],
        "操作系统": f"{platform.system()} {platform.machine()}",
    }


def _collect_context_snapshot() -> dict:
    """收集上下文变量快照（脱敏处理）"""
    from utils.context import context

    all_vars = context.get_all()
    if not all_vars:
        return {}
    return _mask_sensitive(all_vars)


def _mask_sensitive(data: dict) -> dict:
    """对敏感字段进行脱敏（保留前 3 字符 + ***）"""
    masked = {}
    for key, value in data.items():
        if any(s in key.lower() for s in _SENSITIVE_KEYS):
            str_val = str(value)
            if len(str_val) > 3:
                masked[key] = str_val[:3] + "***"
            else:
                masked[key] = "***"
        else:
            masked[key] = value
    return masked


def _format_json(data) -> str:
    """格式化 JSON 输出（dict → 紧凑 JSON 字符串，其他原样）"""
    if isinstance(data, (dict, list)):
        return json.dumps(data, ensure_ascii=False)
    return str(data)


def _extract_trigger_location(traceback_str: str) -> str:
    """从堆栈中提取最后一个项目文件的位置（排除第三方库）"""
    project_root = get_project_root()
    lines = traceback_str.strip().split("\n")

    last_project_file = ""
    for line in lines:
        line = line.strip()
        if line.startswith("File ") and project_root in line:
            # 提取文件名和行号：File "/path/to/file.py", line 72, in func_name
            match = re.search(r'File "(.+?)", line (\d+), in (.+)', line)
            if match:
                file_path = match.group(1).replace(project_root + "/", "")
                line_num = match.group(2)
                func_name = match.group(3)
                last_project_file = f"{file_path}::{func_name} (line {line_num})"
    return last_project_file


def _append_to_bugfix(content: str):
    """追加内容到 BUGFIX.md"""
    # 如果文件不存在，先写标题
    if not os.path.isfile(_BUGFIX_PATH):
        with open(_BUGFIX_PATH, "w", encoding="utf-8") as file:
            file.write("# Bug 记录\n\n")

    with open(_BUGFIX_PATH, "a", encoding="utf-8") as file:
        file.write(content)


def _run_test_case(case_file: str) -> dict:
    """
    运行测试用例

    :param case_file: 用例文件路径
    :return: 测试结果
    """
    import subprocess

    # 根据用例文件确定测试命令
    if case_file.endswith(".yaml"):
        # YAML 用例
        test_cmd = f"python3 -m pytest testcases/test_demo.py::test_yaml_driven -v -k '{os.path.basename(case_file)}'"
    elif case_file.endswith(".json"):
        # JSON 用例
        test_cmd = f"python3 -m pytest testcases/test_demo.py::test_json_driven -v -k '{os.path.basename(case_file)}'"
    elif case_file.endswith(".csv"):
        # CSV 用例
        test_cmd = f"python3 -m pytest testcases/test_demo.py::test_csv_driven -v -k '{os.path.basename(case_file)}'"
    else:
        # 默认运行所有测试
        test_cmd = "python3 -m pytest testcases/ -v"

    try:
        result = subprocess.run(
            test_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        success = result.returncode == 0
        return {
            "success": success,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "测试超时"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== Bug 查询和更新功能 ====================


def get_bug_info(bug_id: str) -> dict:
    """
    获取指定 Bug 的详细信息

    :param bug_id: Bug 编号，如 "BUG-001"
    :return: Bug 信息字典
    """
    if not os.path.isfile(_BUGFIX_PATH):
        return {}

    bug_id = bug_id.upper()
    if not bug_id.startswith("BUG-"):
        bug_id = f"BUG-{bug_id}"

    with open(_BUGFIX_PATH, "r", encoding="utf-8") as file:
        content = file.read()

    # 提取 Bug 信息
    pattern = rf"## {bug_id}：(.*?)\n\n(.*?)(?=## BUG-\d+|$)"
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        return {}

    title = match.group(1).strip()
    details = match.group(2).strip()

    # 解析 Bug 信息
    bug_info = {
        "bug_id": bug_id,
        "title": title,
        "details": details,
    }

    # 提取状态
    status_match = re.search(r"- \*\*状态\*\*：(.+)", details)
    if status_match:
        bug_info["status"] = status_match.group(1).strip()

    # 提取用例文件
    case_file_match = re.search(r"- \*\*用例文件\*\*：(.+)", details)
    if case_file_match:
        bug_info["case_file"] = case_file_match.group(1).strip()

    return bug_info


def list_bugs(status: str = None) -> list:
    """
    列出所有 Bug

    :param status: 按状态筛选 (None/全部, "待修复", "已修复", "无法复现", "重复", "延期")
    :return: Bug 列表
    """
    if not os.path.isfile(_BUGFIX_PATH):
        return []

    with open(_BUGFIX_PATH, "r", encoding="utf-8") as file:
        content = file.read()

    bugs = []
    pattern = r"## (BUG-\d+)：(.*?)\n\n(.*?)(?=## BUG-\d+|$)"
    matches = re.finditer(pattern, content, re.DOTALL)

    for match in matches:
        bug_id = match.group(1)
        title = match.group(2).strip()
        details = match.group(3).strip()

        # 提取状态
        status_match = re.search(r"- \*\*状态\*\*：(.+)", details)
        bug_status = status_match.group(1).strip() if status_match else "未知"

        # 按状态筛选
        if status and bug_status != status:
            continue

        bugs.append({
            "bug_id": bug_id,
            "title": title,
            "status": bug_status,
        })

    return bugs


def update_bug_status(bug_id: str, status: str, fix_commit: str = "", fix_note: str = ""):
    """
    更新 Bug 状态

    :param bug_id: Bug 编号
    :param status: 状态 ("已修复" / "待修复" / "无法复现" / "重复" / "延期")
    :param fix_commit: 修复提交 ID
    :param fix_note: 修复说明
    """
    if not os.path.isfile(_BUGFIX_PATH):
        raise FileNotFoundError(f"BUGFIX.md 文件不存在")

    bug_id = bug_id.upper()
    if not bug_id.startswith("BUG-"):
        bug_id = f"BUG-{bug_id}"

    with open(_BUGFIX_PATH, "r", encoding="utf-8") as file:
        content = file.read()

    # 状态图标映射
    status_icons = {
        "已修复": "✅",
        "待修复": "❌",
        "无法复现": "⚠️",
        "重复": "🔄",
        "延期": "📅",
    }
    status_icon = status_icons.get(status, "❌")

    # 更新状态
    pattern = rf"(## {bug_id}：.*?\n.*?- \*\*状态\*\*：)[^\n]+"
    replacement = rf"\1 {status_icon} {status}"
    new_content = re.sub(pattern, replacement, content)

    # 添加修复验证记录
    if fix_commit or fix_note:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        verification_record = f"""
### 修复验证
- **验证时间**：{now}
- **验证结果**：✅ 通过
- **修复提交**：{fix_commit}
- **修复说明**：{fix_note}
"""
        # 在 "### 原因分析" 之前插入修复验证记录
        pattern = rf"(## {bug_id}：.*?)(### 原因分析)"
        new_content = re.sub(pattern, rf"\1{verification_record}\n\2", new_content, flags=re.DOTALL)

    with open(_BUGFIX_PATH, "w", encoding="utf-8") as file:
        file.write(new_content)

    logger.info("✅ 已更新 %s 状态为 %s", bug_id, status)


def verify_all_bugs(auto_update: bool = True, force: bool = False) -> dict:
    """
    验证所有待修复的 Bug

    :param auto_update: 是否自动更新 BUGFIX.md
    :param force: 强制验证 Bug（忽略开关配置）
    :return: 验证结果汇总
    """
    # 检查 Bug 模式开关
    if _BUG_MODE != "verify" and not force:
        logger.debug("🚫 Bug 模式为 %s，跳过批量验证", _BUG_MODE)
        return {"success": False, "error": f"Bug 模式为 {_BUG_MODE}，无法验证 Bug"}

    bugs = list_bugs(status="待修复")
    if not bugs:
        return {"success": True, "message": "没有待修复的 Bug"}

    results = {
        "total": len(bugs),
        "passed": 0,
        "failed": 0,
        "details": [],
    }

    for bug in bugs:
        bug_id = bug["bug_id"]
        result = _verify_bug_fix(bug_id, auto_update=auto_update)
        results["details"].append({
            "bug_id": bug_id,
            "result": result,
        })
        if result["success"]:
            results["passed"] += 1
        else:
            results["failed"] += 1

    return results


# ==================== 兼容别名 ====================

# 为了兼容旧代码，保留 report_bug 和 verify_bug_fix 作为别名
# 注意：这些别名会强制使用对应的模式，忽略配置文件中的 bug.mode

def report_bug(**kwargs):
    """
    记录 Bug（兼容旧代码）
    强制使用 report 模式，忽略配置文件中的 bug.mode
    """
    return _report_bug(**kwargs)


def verify_bug_fix(**kwargs):
    """
    验证 Bug 修复（兼容旧代码）
    强制使用 verify 模式，忽略配置文件中的 bug.mode
    """
    return _verify_bug_fix(**kwargs)
