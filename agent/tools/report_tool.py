"""
测试报告生成工具

将 Agent 的测试结果持久化为 HTML 和 JSON 报告文件。
报告保存在 reports/ 目录，文件名包含时间戳便于追溯。
"""
import json
import logging
import os
import re
from datetime import datetime

from langchain_core.tools import tool

from config.settings import get_project_root

logger = logging.getLogger(__name__)


def _get_reports_dir() -> str:
    """获取报告输出目录，不存在则创建"""
    reports_dir = os.path.join(get_project_root(), "reports")
    os.makedirs(reports_dir, exist_ok=True)
    return reports_dir


def _generate_timestamp() -> str:
    """生成时间戳字符串，用于文件命名"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _sanitize_filename(title: str) -> str:
    """从报告标题中提取安全的文件名片段"""
    cleaned = re.sub(r'[（(][^）)]*[）)]', '', title)
    cleaned = re.sub(r'[^\w\u4e00-\u9fff-]', '_', cleaned)
    cleaned = re.sub(r'_+', '_', cleaned).strip('_')
    # 限制长度，避免文件名过长
    return cleaned[:40] if cleaned else "report"


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f7fa; color: #333; padding: 24px; }}
  .container {{ max-width: 960px; margin: 0 auto; }}
  h1 {{ font-size: 24px; margin-bottom: 8px; color: #1a1a2e; }}
  .meta {{ color: #666; font-size: 14px; margin-bottom: 24px; }}
  .summary {{ display: flex; gap: 16px; margin-bottom: 24px; }}
  .card {{ flex: 1; background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); text-align: center; }}
  .card .number {{ font-size: 32px; font-weight: 700; }}
  .card .label {{ font-size: 13px; color: #888; margin-top: 4px; }}
  .card.total .number {{ color: #1a1a2e; }}
  .card.pass .number {{ color: #22c55e; }}
  .card.fail .number {{ color: #ef4444; }}
  .card.rate .number {{ color: #3b82f6; }}
  table {{ width: 100%; border-collapse: collapse; background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
  th {{ background: #1a1a2e; color: #fff; padding: 12px 16px; text-align: left; font-size: 13px; font-weight: 600; }}
  td {{ padding: 10px 16px; border-bottom: 1px solid #eee; font-size: 14px; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: #f8f9fb; }}
  .pass-badge {{ color: #22c55e; font-weight: 600; }}
  .fail-badge {{ color: #ef4444; font-weight: 600; }}
  .detail {{ margin-top: 24px; }}
  .detail h2 {{ font-size: 18px; margin-bottom: 12px; color: #1a1a2e; }}
  .step {{ background: #fff; border-radius: 8px; padding: 16px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }}
  .step-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }}
  .step-name {{ font-weight: 600; }}
  pre {{ background: #f1f3f5; padding: 12px; border-radius: 6px; font-size: 13px; overflow-x: auto; margin-top: 8px; white-space: pre-wrap; word-break: break-all; }}
  .req-resp {{ display: flex; gap: 12px; margin-top: 10px; }}
  .req-resp > div {{ flex: 1; min-width: 0; }}
  .req-resp h4 {{ font-size: 12px; color: #666; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.5px; }}
  .req-resp pre {{ background: #1a1a2e; color: #e2e8f0; font-size: 12px; border-radius: 6px; padding: 10px 12px; max-height: 300px; overflow-y: auto; }}
  .toggle-btn {{ background: none; border: 1px solid #ddd; color: #666; font-size: 12px; padding: 3px 10px; border-radius: 4px; cursor: pointer; margin-top: 8px; }}
  .toggle-btn:hover {{ background: #f0f0f0; border-color: #bbb; }}
  .collapsible {{ display: none; }}
  .collapsible.open {{ display: block; }}
  .footer {{ text-align: center; color: #aaa; font-size: 12px; margin-top: 32px; }}
</style>
<script>
function toggleDetail(id) {{
  var el = document.getElementById(id);
  var btn = el.previousElementSibling;
  if (el.classList.contains('open')) {{
    el.classList.remove('open');
    btn.textContent = '\u25b6 \u67e5\u770b\u8bf7\u6c42/\u54cd\u5e94';
  }} else {{
    el.classList.add('open');
    btn.textContent = '\u25bc \u6536\u8d77\u8bf7\u6c42/\u54cd\u5e94';
  }}
}}
</script>
</head>
<body>
<div class="container">
  <h1>{title}</h1>
  <div class="meta">{environment} &middot; {timestamp} &middot; 耗时 {duration}</div>
  <div class="summary">
    <div class="card total"><div class="number">{total}</div><div class="label">总用例</div></div>
    <div class="card pass"><div class="number">{passed}</div><div class="label">通过</div></div>
    <div class="card fail"><div class="number">{failed}</div><div class="label">失败</div></div>
    <div class="card rate"><div class="number">{pass_rate}</div><div class="label">通过率</div></div>
  </div>
  <table>
    <thead><tr><th>#</th><th>用例名称</th><th>方法</th><th>接口</th><th>状态码</th><th>耗时</th><th>结果</th></tr></thead>
    <tbody>{table_rows}</tbody>
  </table>
  {detail_section}
  <div class="footer">Generated by apitestzgs-ai Agent</div>
</div>
</body>
</html>"""


@tool
def save_test_report(report_json: str) -> str:
    """保存测试报告到 reports/ 目录，生成 HTML 和 JSON 两种格式。

    测试全部完成后调用此工具，将测试结果持久化为报告文件。

    Args:
        report_json: 测试报告数据，JSON 字符串格式，结构如下:
            {
                "title": "报告标题（如：用户接口测试报告）",
                "environment": "测试环境（如：test）",
                "duration": "总耗时（如：12.5s）",
                "cases": [
                    {
                        "name": "用例名称",
                        "method": "GET",
                        "url": "/api/users/1",
                        "status_code": 200,
                        "expected_status": 200,
                        "duration": "0.35s",
                        "result": "pass",
                        "request_headers": "{\"Authorization\": \"Bearer xxx\"}",
                        "request_body": "{\"username\": \"test\"}",
                        "response_body": "{\"code\": 200, \"data\": {...}}",
                        "assertions": [
                            {"check": "状态码 200", "result": "pass", "detail": "200 == 200"},
                            {"check": "$.id == 1", "result": "pass", "detail": "字段值匹配"}
                        ],
                        "error": ""
                    }
                ]
            }

            注意：每个 case 必须包含 request_body（请求体，无则传空字符串）和 response_body（完整响应体 JSON 字符串），
            这两个字段会在报告详情中展示，方便排查问题。request_headers 可选，记录请求头信息。

    Returns:
        生成结果，包含报告文件路径
    """
    try:
        report_data = json.loads(report_json)
    except (json.JSONDecodeError, TypeError) as exc:
        return f"❌ 报告数据 JSON 解析失败: {exc}"

    title = report_data.get("title", "API 测试报告")
    environment = report_data.get("environment", "unknown")
    duration = report_data.get("duration", "N/A")
    cases = report_data.get("cases", [])

    if not cases:
        return "❌ 报告中没有测试用例数据"

    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_timestamp = _generate_timestamp()
    safe_name = _sanitize_filename(title)

    # 统计
    total = len(cases)
    passed = sum(1 for case in cases if case.get("result") == "pass")
    failed = total - passed
    pass_rate = f"{(passed / total * 100):.0f}%" if total > 0 else "0%"

    # ========== 生成 HTML ==========
    table_rows = ""
    detail_section = '<div class="detail"><h2>详细结果</h2>'

    for index, case in enumerate(cases, 1):
        case_result = case.get("result", "fail")
        result_badge = '<span class="pass-badge">✅ PASS</span>' if case_result == "pass" else '<span class="fail-badge">❌ FAIL</span>'

        table_rows += (
            f"<tr>"
            f"<td>{index}</td>"
            f"<td>{_escape_html(case.get('name', ''))}</td>"
            f"<td>{_escape_html(case.get('method', ''))}</td>"
            f"<td>{_escape_html(case.get('url', ''))}</td>"
            f"<td>{case.get('status_code', '')}</td>"
            f"<td>{_escape_html(case.get('duration', ''))}</td>"
            f"<td>{result_badge}</td>"
            f"</tr>"
        )

        # 详细断言信息
        assertions = case.get("assertions", [])
        error_msg = case.get("error", "")
        assertion_html = ""
        for assertion in assertions:
            check_result = assertion.get("result", "fail")
            icon = "✅" if check_result == "pass" else "❌"
            assertion_html += f"<div>{icon} {_escape_html(assertion.get('check', ''))} — {_escape_html(assertion.get('detail', ''))}</div>"

        if error_msg:
            assertion_html += f'<pre>错误: {_escape_html(error_msg)}</pre>'

        # 请求/响应详情
        request_body = case.get("request_body", "")
        response_body = case.get("response_body", "")
        request_headers = case.get("request_headers", "")

        req_resp_html = ""
        if request_body or response_body or request_headers:
            toggle_id = f"detail-{index}"
            req_resp_html = f'<button class="toggle-btn" onclick="toggleDetail(\'{toggle_id}\')">▶ 查看请求/响应</button>'
            req_resp_html += f'<div id="{toggle_id}" class="collapsible">'
            req_resp_html += '<div class="req-resp">'

            # 请求侧
            req_resp_html += '<div>'
            req_resp_html += '<h4>📤 Request</h4>'
            if request_headers:
                formatted_headers = _format_json_safe(request_headers)
                req_resp_html += f'<pre>{_escape_html(formatted_headers)}</pre>'
            if request_body:
                formatted_request = _format_json_safe(request_body)
                req_resp_html += f'<pre>{_escape_html(formatted_request)}</pre>'
            elif not request_headers:
                req_resp_html += '<pre>(无请求体)</pre>'
            req_resp_html += '</div>'

            # 响应侧
            req_resp_html += '<div>'
            req_resp_html += '<h4>📥 Response</h4>'
            if response_body:
                formatted_response = _format_json_safe(response_body)
                req_resp_html += f'<pre>{_escape_html(formatted_response)}</pre>'
            else:
                req_resp_html += '<pre>(无响应体)</pre>'
            req_resp_html += '</div>'

            req_resp_html += '</div></div>'

        step_badge = '<span class="pass-badge">PASS</span>' if case_result == "pass" else '<span class="fail-badge">FAIL</span>'
        detail_section += (
            f'<div class="step">'
            f'<div class="step-header"><span class="step-name">#{index} {_escape_html(case.get("name", ""))}</span>{step_badge}</div>'
            f'<div>{_escape_html(case.get("method", ""))} {_escape_html(case.get("url", ""))} → {case.get("status_code", "")}</div>'
            f'{assertion_html}'
            f'{req_resp_html}'
            f'</div>'
        )

    detail_section += "</div>"

    html_content = HTML_TEMPLATE.format(
        title=_escape_html(title),
        environment=_escape_html(environment),
        timestamp=timestamp_str,
        duration=_escape_html(duration),
        total=total,
        passed=passed,
        failed=failed,
        pass_rate=pass_rate,
        table_rows=table_rows,
        detail_section=detail_section,
    )

    # ========== 写入文件 ==========
    reports_dir = _get_reports_dir()
    html_filename = f"{safe_name}_{file_timestamp}.html"
    json_filename = f"{safe_name}_{file_timestamp}.json"

    html_path = os.path.join(reports_dir, html_filename)
    json_path = os.path.join(reports_dir, json_filename)

    # 写 HTML
    with open(html_path, "w", encoding="utf-8") as html_file:
        html_file.write(html_content)

    # 写 JSON（结构化数据，方便程序消费）
    json_report = {
        "title": title,
        "environment": environment,
        "timestamp": timestamp_str,
        "duration": duration,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": pass_rate,
        },
        "cases": cases,
    }
    with open(json_path, "w", encoding="utf-8") as json_file:
        json.dump(json_report, json_file, ensure_ascii=False, indent=2)

    logger.info("测试报告已生成: %s, %s", html_path, json_path)

    return (
        f"✅ 测试报告已生成\n"
        f"  HTML 报告: reports/{html_filename}\n"
        f"  JSON 报告: reports/{json_filename}\n"
        f"  总计: {total} 条用例 | 通过: {passed} | 失败: {failed} | 通过率: {pass_rate}"
    )


def _format_json_safe(data) -> str:
    """将数据格式化为美观的 JSON 字符串，非 JSON 数据原样返回"""
    if isinstance(data, str):
        try:
            parsed = json.loads(data)
            return json.dumps(parsed, ensure_ascii=False, indent=2)
        except (json.JSONDecodeError, TypeError):
            return data
    elif isinstance(data, (dict, list)):
        return json.dumps(data, ensure_ascii=False, indent=2)
    return str(data)


def _escape_html(text: str) -> str:
    """转义 HTML 特殊字符"""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
