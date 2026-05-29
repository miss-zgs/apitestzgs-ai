# Bug 记录

## BUG-001：飞猪查价用例 useTime 写死日期，过期后全链路失败

- **发现时间**：2026-05-29 15:47
- **严重程度**：🔴 高（影响飞猪全链路用例）
- **状态**：✅ 已修复

### 现象

飞猪接机用例 `test_fliggy_pickup_price` 在 2026-05-29 运行时，查价接口返回"搜索结果为空"，导致 `quotation_code` 提取失败，创单用例发送了未替换的原始变量 `${quotation_code}`。

### 请求与响应

**查价请求：**

```
[R-3669] >>> [POST] https://test-gateway-travelswitch.fliggy.com/open/distribution/daolvetravel/openapiSupplier/queryPrice (attempt 1)
[R-3669]     Body: {
  "flightNumber": "K6789",
  "endPoint": {"coordinates": {"lat": 34.6734038, "lon": 135.5013019}, "name": "大丸(心斋桥店)", "type": "2"},
  "startPoint": {"iata": "KIX", "name": "关西国际机场", "type": "1"},
  "luggage": 1,
  "passengers": 3,
  "useTime": "2026-05-28 21:44:00"    ← 写死的日期，已过期
}
```

**查价响应：**

```
[R-3669] <<< [200] .../queryPrice (1.008s)
[R-3669]     Response: {'success': False, 'code': 500, 'message': '搜索结果为空'}
```

**变量提取失败日志：**

```
WARNING - 提取变量失败: quotation_code (jsonpath '$.data.vehicleQuotationList[0].quotationCode' 未匹配)
WARNING - 变量 '${quotation_code}' 未定义，保持原样
```

**创单请求（变量未替换）：**

```
[R-dfb2]     Body: {
  "quotationCode": "${quotation_code}",    ← 未替换，原样发送
  "amount": 360,
  ...
}
```

**创单响应：**

```
[R-dfb2]     Response: {'success': False, 'code': 500, 'message': '系统异常，请联系管理员'}
```

### 根因分析

`data/test_fliggy_pickup.yaml` 中查价和创单的 `useTime` 均写死为 `2026-05-28`：

```yaml
useTime: "2026-05-28 21:44:00"    # 查价
useTime: "2026-05-28 13:55:00"    # 创单
```

接机查价接口要求 `useTime` 必须是**未来时间**，过了 2026-05-28 后该用例就永远失败。

### 影响范围

- `test_fliggy_pickup_price` — 飞猪查价+创单全链路用例
- 其他用例不受影响

### 修复方案

1. **`testcases/conftest.py`** — 在 `inject_env_variables` fixture 中注入 `${tomorrow}` 动态变量：

```python
from datetime import datetime, timedelta
tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
context.set("tomorrow", tomorrow)
```

2. **`data/test_fliggy_pickup.yaml`** — `useTime` 改为动态引用：

```yaml
useTime: "${tomorrow} 21:44:00"    # 查价
useTime: "${tomorrow} 13:55:00"    # 创单
```

### 修复验证

修复后运行结果：

```
[R-db96]     Body: {..., "useTime": "2026-05-30 21:44:00"}     ← 动态明天日期
提取变量: quotation_code = '2247552092###eJyyy...'              ← 提取成功
[R-aa70]     Body: {"quotationCode": "2247552092###eJyyy..."}  ← 变量替换成功
PASSED
```

### 修复提交

```
commit 4aa7f1d
fix: 飞猪用例 useTime 改为动态日期，避免过期导致查价失败
```

---

## BUG-002：http_client.py 请求唯一标识 [R-xxxx] 丢失

- **发现时间**：2026-05-27 17:53
- **严重程度**：🟡 中（不影响功能，影响日志排查效率）
- **状态**：✅ 已修复

### 现象

日志中请求和响应不再带 `[R-xxxx]` 唯一标识，无法通过 grep 快速定位某次请求的完整链路。

**修复前日志：**

```
>>> [POST] https://xxx/queryPrice (attempt 1)
<<< [200] https://xxx/queryPrice (3.815s)
```

**修复后日志：**

```
[R-0c11] >>> [POST] https://xxx/queryPrice (attempt 1)
[R-0c11] <<< [200] https://xxx/queryPrice (4.676s)
```

### 根因分析

Git rebase 时 `utils/http_client.py` 被远程旧版本覆盖，丢失了以下代码：

- `import uuid`
- `request_id = f"R-{uuid.uuid4().hex[:4]}"` 生成唯一标识
- `_log_request` / `_log_response` 方法中的 `request_id` 参数和日志格式

### 修复方案

恢复 `uuid` 导入，在 `_request` 方法中生成 `request_id`，传入日志方法并在每条日志前缀添加 `[R-xxxx]`。

### 修复提交

```
commit 46f76e3
feat: 接口依赖编排+变量提取替换 & utils优化合并
```

---

## BUG-003：查价响应 jsonpath 提取路径错误

- **发现时间**：2026-05-27 17:42
- **严重程度**：🔴 高（导致创单用例无法获取 quotationCode）
- **状态**：✅ 已修复

### 现象

查价接口返回 200 成功，但 `quotation_code` 提取失败，日志报 `KeyError: 0`。

### 请求与响应

**查价响应结构：**

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "vehicleQuotationList": [
      {"quotationCode": "2247552092###...", "baseAmount": 60, ...},
      {"quotationCode": "2247552092###...", "baseAmount": 300, ...}
    ]
  }
}
```

### 根因分析

用例中 extract 的 jsonpath 写成了 `$.data.quotationCode`，但实际响应结构中 `quotationCode` 在 `data.vehicleQuotationList` 数组内部。

| 错误写法 | 正确写法 |
|----------|----------|
| `$.data.quotationCode` | `$.data.vehicleQuotationList[0].quotationCode` |

### 修复方案

`data/test_fliggy_pickup.yaml` 中修正 jsonpath：

```yaml
extract:
  quotation_code: $.data.vehicleQuotationList[0].quotationCode
```

### 修复提交

```
commit 46f76e3
feat: 接口依赖编排+变量提取替换 & utils优化合并
```
## BUG-004：调试测试-断言失败 - 状态码不匹配: 期望 666, 实际 200
响应内容: {
  "userId": 1,
  "id": 1,
  "title": "sunt aut fa

- **发现时间**：2026-05-29 16:54:14
- **严重程度**：🔴 高
- **状态**：❌ 待修复

### 报错位置
- **用例名称**：调试测试-断言失败
- **用例文件**：data/调试测试.yaml（步骤 1/1）
- **触发位置**：utils/assertion.py::assert_status_code (line 16)

### 环境信息
- **运行环境**：test
- **Base URL**：https://jsonplaceholder.typicode.com
- **Python 版本**：3.14.2
- **操作系统**：Darwin arm64

### 请求信息
- **Method**：GET
- **URL**：https://jsonplaceholder.typicode.com/posts/1

### 响应信息
- **Status Code**：200
- **耗时**：0.599s
- **Response Body**：
  ```json
  {"userId": 1, "id": 1, "title": "sunt aut facere repellat provident occaecati excepturi optio reprehenderit", "body": "quia et suscipit\nsuscipit recusandae consequuntur expedita et cum\nreprehenderit molestiae ut ut quas totam\nnostrum rerum est autem sunt rem eveniet architecto"}
  ```

### 报错信息
```
状态码不匹配: 期望 666, 实际 200
响应内容: {
  "userId": 1,
  "id": 1,
  "title": "sunt aut facere repellat provident occaecati excepturi optio reprehenderit",
  "body": "quia et suscipit\nsuscipit recusandae consequuntur expedita et cum\nreprehenderit molestiae ut ut quas totam\nnostrum rerum est autem sunt rem eveniet architecto"
}
```

### 完整堆栈
```
Traceback (most recent call last):
  File "/Users/zhou/api_test_zhou/PythonProject/PythonProject/apitestzgs/utils/case_executor.py", line 106, in execute_chain
    assert_by_expect(response, resolve_variables(expect))
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/zhou/api_test_zhou/PythonProject/PythonProject/apitestzgs/utils/assertion.py", line 97, in assert_by_expect
    assert_status_code(response, int(expect["status_code"]))
    ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/zhou/api_test_zhou/PythonProject/PythonProject/apitestzgs/utils/assertion.py", line 16, in assert_status_code
    assert actual == expected_code, (
           ^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 状态码不匹配: 期望 666, 实际 200
响应内容: {
  "userId": 1,
  "id": 1,
  "title": "sunt aut facere repellat provident occaecati excepturi optio reprehenderit",
  "body": "quia et suscipit\nsuscipit recusandae consequuntur expedita et cum\nreprehenderit molestiae ut ut quas totam\nnostrum rerum est autem sunt rem eveniet architecto"
}
```

### 上下文变量快照
```json
{
  "timestamp": "1780044853",
  "tomorrow": "2026-05-30"
}
```

### 原因分析
待分析

### 复现步骤
```bash
python3 -m pytest testcases/ -v
```

---
## BUG-005：调试测试-断言失败 - 状态码不匹配: 期望 666, 实际 200
响应内容: {
  "userId": 1,
  "id": 1,
  "title": "sunt aut fa

- **发现时间**：2026-05-29 16:54:44
- **严重程度**：🔴 高
- **状态**：❌ 待修复

### 报错位置
- **用例名称**：调试测试-断言失败
- **用例文件**：data/调试测试.yaml（步骤 1/1）
- **触发位置**：utils/assertion.py::assert_status_code (line 16)

### 环境信息
- **运行环境**：test
- **Base URL**：https://jsonplaceholder.typicode.com
- **Python 版本**：3.14.2
- **操作系统**：Darwin arm64

### 请求信息
- **Method**：GET
- **URL**：https://jsonplaceholder.typicode.com/posts/1

### 响应信息
- **Status Code**：200
- **耗时**：1.732s
- **Response Body**：
  ```json
  {"userId": 1, "id": 1, "title": "sunt aut facere repellat provident occaecati excepturi optio reprehenderit", "body": "quia et suscipit\nsuscipit recusandae consequuntur expedita et cum\nreprehenderit molestiae ut ut quas totam\nnostrum rerum est autem sunt rem eveniet architecto"}
  ```

### 报错信息
```
状态码不匹配: 期望 666, 实际 200
响应内容: {
  "userId": 1,
  "id": 1,
  "title": "sunt aut facere repellat provident occaecati excepturi optio reprehenderit",
  "body": "quia et suscipit\nsuscipit recusandae consequuntur expedita et cum\nreprehenderit molestiae ut ut quas totam\nnostrum rerum est autem sunt rem eveniet architecto"
}
```

### 完整堆栈
```
Traceback (most recent call last):
  File "/Users/zhou/api_test_zhou/PythonProject/PythonProject/apitestzgs/utils/case_executor.py", line 106, in execute_chain
    assert_by_expect(response, resolve_variables(expect))
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/zhou/api_test_zhou/PythonProject/PythonProject/apitestzgs/utils/assertion.py", line 97, in assert_by_expect
    assert_status_code(response, int(expect["status_code"]))
    ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/zhou/api_test_zhou/PythonProject/PythonProject/apitestzgs/utils/assertion.py", line 16, in assert_status_code
    assert actual == expected_code, (
           ^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 状态码不匹配: 期望 666, 实际 200
响应内容: {
  "userId": 1,
  "id": 1,
  "title": "sunt aut facere repellat provident occaecati excepturi optio reprehenderit",
  "body": "quia et suscipit\nsuscipit recusandae consequuntur expedita et cum\nreprehenderit molestiae ut ut quas totam\nnostrum rerum est autem sunt rem eveniet architecto"
}
```

### 原因分析
待分析

### 复现步骤
```bash
python3 -m pytest testcases/ -v
```

---
## BUG-006：断言失败演示 - 状态码不匹配: 期望 666, 实际 200
响应内容: {
  "userId": 1,
  "id": 1,
  "title": "sunt aut fa

- **发现时间**：2026-05-29 16:57:40
- **严重程度**：🔴 高
- **状态**：❌ 待修复

### 报错位置
- **用例名称**：断言失败演示
- **用例文件**：data/assertion_failure_demo.yaml（步骤 1/1）
- **触发位置**：utils/assertion.py::assert_status_code (line 16)

### 环境信息
- **运行环境**：test
- **Base URL**：https://jsonplaceholder.typicode.com
- **Python 版本**：3.14.2
- **操作系统**：Darwin arm64

### 请求信息
- **Method**：GET
- **URL**：https://jsonplaceholder.typicode.com/posts/1

### 响应信息
- **Status Code**：200
- **耗时**：0.635s
- **Response Body**：
  ```json
  {"userId": 1, "id": 1, "title": "sunt aut facere repellat provident occaecati excepturi optio reprehenderit", "body": "quia et suscipit\nsuscipit recusandae consequuntur expedita et cum\nreprehenderit molestiae ut ut quas totam\nnostrum rerum est autem sunt rem eveniet architecto"}
  ```

### 报错信息
```
状态码不匹配: 期望 666, 实际 200
响应内容: {
  "userId": 1,
  "id": 1,
  "title": "sunt aut facere repellat provident occaecati excepturi optio reprehenderit",
  "body": "quia et suscipit\nsuscipit recusandae consequuntur expedita et cum\nreprehenderit molestiae ut ut quas totam\nnostrum rerum est autem sunt rem eveniet architecto"
}
```

### 完整堆栈
```
Traceback (most recent call last):
  File "/Users/zhou/api_test_zhou/PythonProject/PythonProject/apitestzgs/utils/case_executor.py", line 106, in execute_chain
    assert_by_expect(response, resolve_variables(expect))
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/zhou/api_test_zhou/PythonProject/PythonProject/apitestzgs/utils/assertion.py", line 97, in assert_by_expect
    assert_status_code(response, int(expect["status_code"]))
    ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/zhou/api_test_zhou/PythonProject/PythonProject/apitestzgs/utils/assertion.py", line 16, in assert_status_code
    assert actual == expected_code, (
           ^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 状态码不匹配: 期望 666, 实际 200
响应内容: {
  "userId": 1,
  "id": 1,
  "title": "sunt aut facere repellat provident occaecati excepturi optio reprehenderit",
  "body": "quia et suscipit\nsuscipit recusandae consequuntur expedita et cum\nreprehenderit molestiae ut ut quas totam\nnostrum rerum est autem sunt rem eveniet architecto"
}
```

### 上下文变量快照
```json
{
  "FLIGGY_CLIENT_ID": "filggy_3IEZ27oCuRqPMpQ",
  "FLIGGY_CLIENT_SECRET": "9F!***",
  "FLIGGY_ENV": "test-",
  "timestamp": "1780045060",
  "tomorrow": "2026-05-30"
}
```

### 原因分析
待分析

### 复现步骤
```bash
python3 -m pytest testcases/ -v
```

---
## BUG-007：断言失败演示 - 状态码不匹配: 期望 666, 实际 200
响应内容: {
  "userId": 1,
  "id": 1,
  "title": "sunt aut fa

- **发现时间**：2026-05-29 17:03:37
- **严重程度**：🔴 高
- **状态**：❌ 待修复

### 报错位置
- **用例名称**：断言失败演示
- **用例文件**：data/assertion_failure_demo.yaml（步骤 1/1）
- **触发位置**：utils/assertion.py::assert_status_code (line 16)

### 环境信息
- **运行环境**：test
- **Base URL**：https://jsonplaceholder.typicode.com
- **Python 版本**：3.14.2
- **操作系统**：Darwin arm64

### 请求信息
- **Method**：GET
- **URL**：https://jsonplaceholder.typicode.com/posts/1

### 响应信息
- **Status Code**：200
- **耗时**：0.213s
- **Response Body**：
  ```json
  {"userId": 1, "id": 1, "title": "sunt aut facere repellat provident occaecati excepturi optio reprehenderit", "body": "quia et suscipit\nsuscipit recusandae consequuntur expedita et cum\nreprehenderit molestiae ut ut quas totam\nnostrum rerum est autem sunt rem eveniet architecto"}
  ```

### 报错信息
```
状态码不匹配: 期望 666, 实际 200
响应内容: {
  "userId": 1,
  "id": 1,
  "title": "sunt aut facere repellat provident occaecati excepturi optio reprehenderit",
  "body": "quia et suscipit\nsuscipit recusandae consequuntur expedita et cum\nreprehenderit molestiae ut ut quas totam\nnostrum rerum est autem sunt rem eveniet architecto"
}
```

### 完整堆栈
```
Traceback (most recent call last):
  File "/Users/zhou/api_test_zhou/PythonProject/PythonProject/apitestzgs/utils/case_executor.py", line 106, in execute_chain
    assert_by_expect(response, resolve_variables(expect))
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/zhou/api_test_zhou/PythonProject/PythonProject/apitestzgs/utils/assertion.py", line 97, in assert_by_expect
    assert_status_code(response, int(expect["status_code"]))
    ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/zhou/api_test_zhou/PythonProject/PythonProject/apitestzgs/utils/assertion.py", line 16, in assert_status_code
    assert actual == expected_code, (
           ^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 状态码不匹配: 期望 666, 实际 200
响应内容: {
  "userId": 1,
  "id": 1,
  "title": "sunt aut facere repellat provident occaecati excepturi optio reprehenderit",
  "body": "quia et suscipit\nsuscipit recusandae consequuntur expedita et cum\nreprehenderit molestiae ut ut quas totam\nnostrum rerum est autem sunt rem eveniet architecto"
}
```

### 上下文变量快照
```json
{
  "FLIGGY_CLIENT_ID": "filggy_3IEZ27oCuRqPMpQ",
  "FLIGGY_CLIENT_SECRET": "9F!***",
  "FLIGGY_ENV": "test-",
  "timestamp": "1780045406",
  "tomorrow": "2026-05-30",
  "post_id": 1,
  "post_user_id": 1,
  "post_title": "sunt aut facere repellat provident occaecati excepturi optio reprehenderit",
  "quotation_code": "2247552092###eJyCyDkOAkEMBMDHTDwr291z5SS8YjWXpQ0gIuAXfBlBhSUfE1EJ2FK6dkZIZWQuHrsDkZqrNw56n2E2zWWI+7ANrN3S2qMb55Rpyz1cr/24P9d+nxoU6TBUQ2oneNCqVvL8dRKF6L9zAQU13ChUZMoX9R0lFw=="
}
```

### 原因分析
待分析

### 复现步骤
```bash
python3 -m pytest testcases/ -v
```

---
## BUG-008：断言失败测试-YAML - 状态码不匹配: 期望 666, 实际 200
响应内容: {
  "userId": 1,
  "id": 1,
  "title": "sunt aut fa

- **发现时间**：2026-05-29 17:13:19
- **严重程度**：🔴 高
- **状态**：❌ 待修复

### 报错位置
- **用例名称**：断言失败测试-YAML
- **用例文件**：data/test_demo.yaml（步骤 1/1）
- **触发位置**：utils/assertion.py::assert_status_code (line 16)

### 环境信息
- **运行环境**：test
- **Base URL**：https://jsonplaceholder.typicode.com
- **Python 版本**：3.14.2
- **操作系统**：Darwin arm64

### 请求信息
- **Method**：GET
- **URL**：/posts/1

### 响应信息
- **Status Code**：200
- **耗时**：0.249s
- **Response Body**：
  ```json
  {"userId": 1, "id": 1, "title": "sunt aut facere repellat provident occaecati excepturi optio reprehenderit", "body": "quia et suscipit\nsuscipit recusandae consequuntur expedita et cum\nreprehenderit molestiae ut ut quas totam\nnostrum rerum est autem sunt rem eveniet architecto"}
  ```

### 报错信息
```
状态码不匹配: 期望 666, 实际 200
响应内容: {
  "userId": 1,
  "id": 1,
  "title": "sunt aut facere repellat provident occaecati excepturi optio reprehenderit",
  "body": "quia et suscipit\nsuscipit recusandae consequuntur expedita et cum\nreprehenderit molestiae ut ut quas totam\nnostrum rerum est autem sunt rem eveniet architecto"
}
```

### 完整堆栈
```
Traceback (most recent call last):
  File "/Users/zhou/api_test_zhou/PythonProject/PythonProject/apitestzgs/testcases/test_demo.py", line 27, in test_yaml_driven
    assert_by_expect(response, case["expect"])
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/zhou/api_test_zhou/PythonProject/PythonProject/apitestzgs/utils/assertion.py", line 97, in assert_by_expect
    assert_status_code(response, int(expect["status_code"]))
    ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/zhou/api_test_zhou/PythonProject/PythonProject/apitestzgs/utils/assertion.py", line 16, in assert_status_code
    assert actual == expected_code, (
           ^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 状态码不匹配: 期望 666, 实际 200
响应内容: {
  "userId": 1,
  "id": 1,
  "title": "sunt aut facere repellat provident occaecati excepturi optio reprehenderit",
  "body": "quia et suscipit\nsuscipit recusandae consequuntur expedita et cum\nreprehenderit molestiae ut ut quas totam\nnostrum rerum est autem sunt rem eveniet architecto"
}
```

### 上下文变量快照
```json
{
  "FLIGGY_CLIENT_ID": "filggy_3IEZ27oCuRqPMpQ",
  "FLIGGY_CLIENT_SECRET": "9F!***",
  "FLIGGY_ENV": "test-",
  "timestamp": "1780045997",
  "tomorrow": "2026-05-30"
}
```

### 原因分析
待分析

### 复现步骤
```bash
python3 -m pytest testcases/ -v
```

---
## BUG-009：断言失败演示 - 状态码不匹配: 期望 666, 实际 200
响应内容: {
  "userId": 1,
  "id": 1,
  "title": "sunt aut fa

- **发现时间**：2026-06-01 13:51:53
- **严重程度**：🔴 高
- **状态**：❌ 待修复

### 报错位置
- **用例名称**：断言失败演示
- **用例文件**：data/assertion_failure_demo.yaml（步骤 1/1）
- **触发位置**：utils/assertion.py::assert_status_code (line 16)

### 环境信息
- **运行环境**：test
- **Base URL**：https://jsonplaceholder.typicode.com
- **Python 版本**：3.14.2
- **操作系统**：Darwin arm64

### 请求信息
- **Method**：GET
- **URL**：https://jsonplaceholder.typicode.com/posts/1

### 响应信息
- **Status Code**：200
- **耗时**：0.77s
- **Response Body**：
  ```json
  {"userId": 1, "id": 1, "title": "sunt aut facere repellat provident occaecati excepturi optio reprehenderit", "body": "quia et suscipit\nsuscipit recusandae consequuntur expedita et cum\nreprehenderit molestiae ut ut quas totam\nnostrum rerum est autem sunt rem eveniet architecto"}
  ```

### 报错信息
```
状态码不匹配: 期望 666, 实际 200
响应内容: {
  "userId": 1,
  "id": 1,
  "title": "sunt aut facere repellat provident occaecati excepturi optio reprehenderit",
  "body": "quia et suscipit\nsuscipit recusandae consequuntur expedita et cum\nreprehenderit molestiae ut ut quas totam\nnostrum rerum est autem sunt rem eveniet architecto"
}
```

### 完整堆栈
```
Traceback (most recent call last):
  File "/Users/zhou/api_test_zhou/PythonProject/PythonProject/apitestzgs/utils/case_executor.py", line 106, in execute_chain
    assert_by_expect(response, resolve_variables(expect))
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/zhou/api_test_zhou/PythonProject/PythonProject/apitestzgs/utils/assertion.py", line 97, in assert_by_expect
    assert_status_code(response, int(expect["status_code"]))
    ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/zhou/api_test_zhou/PythonProject/PythonProject/apitestzgs/utils/assertion.py", line 16, in assert_status_code
    assert actual == expected_code, (
           ^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 状态码不匹配: 期望 666, 实际 200
响应内容: {
  "userId": 1,
  "id": 1,
  "title": "sunt aut facere repellat provident occaecati excepturi optio reprehenderit",
  "body": "quia et suscipit\nsuscipit recusandae consequuntur expedita et cum\nreprehenderit molestiae ut ut quas totam\nnostrum rerum est autem sunt rem eveniet architecto"
}
```

### 上下文变量快照
```json
{
  "FLIGGY_CLIENT_ID": "filggy_3IEZ27oCuRqPMpQ",
  "FLIGGY_CLIENT_SECRET": "9F!***",
  "FLIGGY_ENV": "test-",
  "timestamp": "1780293113",
  "tomorrow": "2026-06-02"
}
```

### 原因分析
待分析

### 复现步骤
```bash
python3 -m pytest testcases/ -v
```

---
## BUG-010：断言失败测试-YAML - 状态码不匹配: 期望 666, 实际 200
响应内容: {
  "userId": 1,
  "id": 1,
  "title": "sunt aut fa

- **发现时间**：2026-06-01 13:59:01
- **严重程度**：🔴 高
- **状态**：❌ 待修复

### 报错位置
- **用例名称**：断言失败测试-YAML
- **用例文件**：data/test_demo.yaml（步骤 1/1）
- **触发位置**：utils/assertion.py::assert_status_code (line 16)

### 环境信息
- **运行环境**：test
- **Base URL**：https://jsonplaceholder.typicode.com
- **Python 版本**：3.14.2
- **操作系统**：Darwin arm64

### 请求信息
- **Method**：GET
- **URL**：/posts/1

### 响应信息
- **Status Code**：200
- **耗时**：0.208s
- **Response Body**：
  ```json
  {"userId": 1, "id": 1, "title": "sunt aut facere repellat provident occaecati excepturi optio reprehenderit", "body": "quia et suscipit\nsuscipit recusandae consequuntur expedita et cum\nreprehenderit molestiae ut ut quas totam\nnostrum rerum est autem sunt rem eveniet architecto"}
  ```

### 报错信息
```
状态码不匹配: 期望 666, 实际 200
响应内容: {
  "userId": 1,
  "id": 1,
  "title": "sunt aut facere repellat provident occaecati excepturi optio reprehenderit",
  "body": "quia et suscipit\nsuscipit recusandae consequuntur expedita et cum\nreprehenderit molestiae ut ut quas totam\nnostrum rerum est autem sunt rem eveniet architecto"
}
```

### 完整堆栈
```
Traceback (most recent call last):
  File "/Users/zhou/api_test_zhou/PythonProject/PythonProject/apitestzgs/testcases/test_demo.py", line 63, in test_yaml_driven
    assert_by_expect(response, case["expect"])
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/zhou/api_test_zhou/PythonProject/PythonProject/apitestzgs/utils/assertion.py", line 97, in assert_by_expect
    assert_status_code(response, int(expect["status_code"]))
    ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/zhou/api_test_zhou/PythonProject/PythonProject/apitestzgs/utils/assertion.py", line 16, in assert_status_code
    assert actual == expected_code, (
           ^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 状态码不匹配: 期望 666, 实际 200
响应内容: {
  "userId": 1,
  "id": 1,
  "title": "sunt aut facere repellat provident occaecati excepturi optio reprehenderit",
  "body": "quia et suscipit\nsuscipit recusandae consequuntur expedita et cum\nreprehenderit molestiae ut ut quas totam\nnostrum rerum est autem sunt rem eveniet architecto"
}
```

### 上下文变量快照
```json
{
  "FLIGGY_CLIENT_ID": "filggy_3IEZ27oCuRqPMpQ",
  "FLIGGY_CLIENT_SECRET": "9F!***",
  "FLIGGY_ENV": "test-",
  "timestamp": "1780293539",
  "tomorrow": "2026-06-02"
}
```

### 原因分析
待分析

### 复现步骤
```bash
python3 -m pytest testcases/ -v
```

---
## BUG-011：断言失败演示 - 状态码不匹配: 期望 666, 实际 200
响应内容: {
  "userId": 1,
  "id": 1,
  "title": "sunt aut fa

- **发现时间**：2026-06-01 13:59:13
- **严重程度**：🔴 高
- **状态**：❌ 待修复

### 报错位置
- **用例名称**：断言失败演示
- **用例文件**：data/assertion_failure_demo.yaml（步骤 1/1）
- **触发位置**：utils/assertion.py::assert_status_code (line 16)

### 环境信息
- **运行环境**：test
- **Base URL**：https://jsonplaceholder.typicode.com
- **Python 版本**：3.14.2
- **操作系统**：Darwin arm64

### 请求信息
- **Method**：GET
- **URL**：https://jsonplaceholder.typicode.com/posts/1

### 响应信息
- **Status Code**：200
- **耗时**：0.206s
- **Response Body**：
  ```json
  {"userId": 1, "id": 1, "title": "sunt aut facere repellat provident occaecati excepturi optio reprehenderit", "body": "quia et suscipit\nsuscipit recusandae consequuntur expedita et cum\nreprehenderit molestiae ut ut quas totam\nnostrum rerum est autem sunt rem eveniet architecto"}
  ```

### 报错信息
```
状态码不匹配: 期望 666, 实际 200
响应内容: {
  "userId": 1,
  "id": 1,
  "title": "sunt aut facere repellat provident occaecati excepturi optio reprehenderit",
  "body": "quia et suscipit\nsuscipit recusandae consequuntur expedita et cum\nreprehenderit molestiae ut ut quas totam\nnostrum rerum est autem sunt rem eveniet architecto"
}
```

### 完整堆栈
```
Traceback (most recent call last):
  File "/Users/zhou/api_test_zhou/PythonProject/PythonProject/apitestzgs/utils/case_executor.py", line 106, in execute_chain
    assert_by_expect(response, resolve_variables(expect))
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/zhou/api_test_zhou/PythonProject/PythonProject/apitestzgs/utils/assertion.py", line 97, in assert_by_expect
    assert_status_code(response, int(expect["status_code"]))
    ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/zhou/api_test_zhou/PythonProject/PythonProject/apitestzgs/utils/assertion.py", line 16, in assert_status_code
    assert actual == expected_code, (
           ^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 状态码不匹配: 期望 666, 实际 200
响应内容: {
  "userId": 1,
  "id": 1,
  "title": "sunt aut facere repellat provident occaecati excepturi optio reprehenderit",
  "body": "quia et suscipit\nsuscipit recusandae consequuntur expedita et cum\nreprehenderit molestiae ut ut quas totam\nnostrum rerum est autem sunt rem eveniet architecto"
}
```

### 上下文变量快照
```json
{
  "FLIGGY_CLIENT_ID": "filggy_3IEZ27oCuRqPMpQ",
  "FLIGGY_CLIENT_SECRET": "9F!***",
  "FLIGGY_ENV": "test-",
  "timestamp": "1780293539",
  "tomorrow": "2026-06-02",
  "post_id": 1,
  "post_user_id": 1,
  "post_title": "sunt aut facere repellat provident occaecati excepturi optio reprehenderit",
  "quotation_code": "2247552092###eJwXyDEOQiEQBcDDUPPzHrvsX3obT0FA2MRCKwtv4ZWNTjn4FIBIbjvCzpbrCsk6tuS5KdkjuLz5dlrimFhq4cQ5dJhNu0UVjAAmmqb7az+uz7XfnYlSjyJepLYuemhxumr/dQUF/LedohBPF4VSTPEF4h0kaw=="
}
```

### 原因分析
待分析

### 复现步骤
```bash
python3 -m pytest testcases/ -v
```

---
