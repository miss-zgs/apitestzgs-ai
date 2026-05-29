"""
示例测试用例 - 数据驱动
使用 JSONPlaceholder 公开 API 进行演示
支持从 YAML / JSON / CSV 加载用例
支持接口依赖编排（串行执行 + 变量提取替换）
"""
import pytest
import traceback
from testcases.conftest import load_cases
from utils.assertion import assert_by_expect
from utils.case_executor import execute_case, execute_chain, parse_csv_case
from utils.bug_reporter import bug_handler


def _report_test_bug(case, response, exc, case_file: str):
    """
    记录测试用例的 Bug 信息

    :param case: 用例字典
    :param response: 响应对象
    :param exc: 异常对象
    :param case_file: 用例文件路径
    """
    request_info = {
        "method": case.get("method", "GET").upper(),
        "url": case.get("url", ""),
        "headers": case.get("headers"),
        "body": case.get("json") or case.get("data"),
    }
    response_info = {
        "status_code": response.status_code,
        "elapsed": round(response.elapsed.total_seconds(), 3),
    }
    try:
        response_info["body"] = response.json()
    except ValueError:
        response_info["body"] = response.text[:500]
    bug_handler(
        bug_title=f"{case.get('case_name', '未命名用例')} - {str(exc)[:80]}",
        severity="高",
        case_name=case.get("case_name", "未命名用例"),
        case_file=case_file,
        step_info="步骤 1/1",
        request_info=request_info,
        response_info=response_info,
        error_message=str(exc),
        traceback_str=traceback.format_exc(),
    )


# ---------- YAML 驱动 ----------

@pytest.mark.parametrize(
    "case",
    load_cases("test_demo.yaml"),
    ids=lambda c: c.get("case_name", ""),
)
def test_yaml_driven(case, http_client):
    """YAML 数据驱动用例"""
    response = execute_case(case, http_client)
    if case.get("expect"):
        try:
            assert_by_expect(response, case["expect"])
        except (AssertionError, Exception) as exc:
            _report_test_bug(case, response, exc, "data/test_demo.yaml")
            raise


# ---------- JSON 驱动 ----------

@pytest.mark.parametrize(
    "case",
    load_cases("test_demo.json"),
    ids=lambda c: c.get("case_name", ""),
)
def test_json_driven(case, http_client):
    """JSON 数据驱动用例"""
    response = execute_case(case, http_client)
    if case.get("expect"):
        try:
            assert_by_expect(response, case["expect"])
        except (AssertionError, Exception) as exc:
            _report_test_bug(case, response, exc, "data/test_demo.json")
            raise


# ---------- CSV 驱动 ----------

@pytest.mark.parametrize(
    "case",
    load_cases("test_demo.csv"),
    ids=lambda c: c.get("case_name", ""),
)
def test_csv_driven(case, http_client):
    """CSV 数据驱动用例"""
    # CSV 读出来的 json/expect 字段是字符串，需要反序列化
    parsed_case = parse_csv_case(case)
    response = execute_case(parsed_case, http_client)
    if parsed_case.get("expect"):
        try:
            assert_by_expect(response, parsed_case["expect"])
        except (AssertionError, Exception) as exc:
            _report_test_bug(parsed_case, response, exc, "data/test_demo.csv")
            raise


# ---------- 接口依赖编排（串行执行） ----------

def test_dependency_chain(http_client):
    """
    接口依赖编排示例：按顺序执行多个接口，上一个接口的返回值传给下一个

    用例文件中通过 extract 提取变量，后续用例通过 ${变量名} 引用
    """
    execute_chain(load_cases("test_dependency.yaml"), http_client, case_file="data/test_dependency.yaml")


# ---------- 飞猪接口测试（串行执行） ----------

def test_fliggy_pickup_price(http_client):
    """飞猪道旅 - 接机查价+创单"""
    execute_chain(load_cases("test_fliggy_pickup.yaml"), http_client, case_file="data/test_fliggy_pickup.yaml")


# ---------- 断言失败测试（用于演示 Bug 自动记录） ----------

def test_assertion_failure_demo(http_client):
    """
    断言失败演示用例 - 用于测试 Bug 自动记录功能
    期望 status_code=666，但实际返回 200，必然失败
    """
    cases = [{
        'case_name': '断言失败演示',
        'method': 'GET',
        'url': 'https://jsonplaceholder.typicode.com/posts/1',
        'expect': {
            'status_code': 666  # 期望 666，实际返回 200，必然失败
        }
    }]
    execute_chain(cases, http_client, case_file="data/assertion_failure_demo.yaml")



