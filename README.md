# API 接口自动化测试框架

基于 Python + Pytest 的通用接口自动化测试框架，开箱即用。

## 前置准备（新电脑必读）

从 Git 拉取项目后，按以下步骤即可运行：

### 1. Python 环境

需要 **Python 3.9+**，确认版本：

```bash
python3 --version
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

项目中的敏感信息（API 密钥等）通过 `.env` 文件管理，**该文件不会被 Git 同步**，需要手动创建：

```bash
cp .env.example .env
```

然后编辑 `.env`，填入真实值：

```
FLIGGY_CLIENT_ID=你的clientId
FLIGGY_CLIENT_SECRET=你的clientSecret
FLIGGY_ENV=test-
```

> ⚠️ 如果不配置 `.env`，飞猪相关用例会失败，但不影响其他用例运行。

### 4. 运行测试

```bash
# 运行全部用例
python3 run.py

# 只运行基础示例用例（不依赖 .env）
python3 -m pytest testcases/test_demo.py::test_yaml_driven -v
```

---

## 核心特性

- **统一请求封装** — GET/POST/PUT/DELETE/PATCH/文件上传，自动重试、日志记录、Session 管理
- **多格式数据驱动** — 支持 YAML / JSON / Excel / CSV 四种用例格式，自动识别加载
- **通用断言工具** — 状态码校验、jsonpath 字段提取校验、包含/类型/非空断言
- **多环境切换** — 通过配置文件一键切换 dev / test / pre / prod
- **接口依赖编排** — 支持接口间串行调用，前一个接口的返回值自动传给下一个
- **变量提取与替换** — `${变量名}` 语法，从响应中用 jsonpath 提取值，后续接口自动引用
- **请求唯一 Key** — 每次请求自动生成唯一标识 `[R-xxxx]`，日志排查一搜即达
- **日志双输出** — 控制台 + 按天切分的日志文件，支持 DEBUG/INFO 级别切换
- **Allure 报告** — 支持生成美观的可视化测试报告

## 项目结构

```
apitestzgs/
├── config/
│   ├── config.yaml          # 环境配置（域名、超时、重试、日志级别等）
│   └── settings.py          # 配置读取工具
├── utils/
│   ├── http_client.py       # 统一 HTTP 请求封装（含唯一 Key、重试、日志）
│   ├── case_executor.py     # 用例执行引擎（execute_case / execute_chain）
│   ├── data_loader.py       # 多格式用例数据加载器
│   ├── assertion.py         # 通用断言工具
│   ├── context.py           # 全局上下文 + 变量解析器（${} 替换 + jsonpath 提取）
│   ├── logger.py            # 日志初始化（控制台 + 文件双输出）
│   └── bug_reporter.py      # Bug 报告工具（自动记录 Bug 到 BUGFIX.md）
├── api/
│   └── base_api.py          # 接口层基类
├── testcases/
│   ├── conftest.py          # pytest fixture（日志初始化、http_client、用例加载）
│   └── test_demo.py         # 示例用例（数据驱动 + 依赖编排）
├── data/
│   ├── test_demo.yaml       # YAML 格式用例（独立接口）
│   ├── test_demo.json       # JSON 格式用例
│   ├── test_demo.csv        # CSV 格式用例
│   ├── test_dependency.yaml # 接口依赖编排用例（串行 + 变量传递）
│   └── test_fliggy_pickup.yaml # 飞猪接机查价+创单用例
├── logs/                    # 日志文件目录（按天切分，自动保留 30 天）
├── reports/                 # 测试报告输出目录
├── example_usage.py         # HttpClient 使用示例（调试学习用）
├── run.py                   # 一键执行入口
├── pytest.ini               # pytest 配置
└── requirements.txt         # 依赖清单
```

## 常用运行方式

```bash
# 指定环境运行
python3 run.py --env dev

# 按关键词筛选用例
python3 run.py -k test_yaml

# 只运行接口依赖编排用例
python3 -m pytest testcases/test_demo.py::test_dependency_chain -v

# 只运行飞猪接口用例
python3 -m pytest testcases/test_demo.py::test_fliggy_pickup_price -v

# 运行 HttpClient 使用示例（调试学习用）
python3 example_usage.py

# 生成 Allure 报告
pytest testcases/ --alluredir=reports/allure-results
allure serve reports/allure-results

# 查看当天日志
cat logs/$(date +%Y-%m-%d).log

# 搜索某次请求的完整链路（用唯一 Key）
grep "R-a3f8" logs/2026-05-27.log
```

## 用例数据格式

### YAML 格式（独立接口）

```yaml
- case_name: "查询用户"
  method: GET
  url: /api/user/1
  params:
    _limit: 10
  headers:
    Authorization: "Bearer xxx"
  expect:
    status_code: 200
    jsonpath:
      $.code: 0
      $.data.name: "张三"
```

### YAML 格式（接口依赖编排）

```yaml
# 步骤1：登录获取 Token
- case_name: "登录"
  method: POST
  url: /api/login
  json:
    username: "admin"
    password: "123456"
  extract:
    token: $.data.token           # 用 jsonpath 从响应中提取 token
    user_id: $.data.id            # 提取 user_id
  expect:
    status_code: 200

# 步骤2：用 Token 查询用户信息（引用上一步提取的变量）
- case_name: "查询当前用户"
  method: GET
  url: /api/user/${user_id}       # ${user_id} 会被替换为步骤1提取的值
  headers:
    Authorization: "Bearer ${token}"  # ${token} 同理
  expect:
    status_code: 200
    jsonpath:
      $.data.id: "${user_id}"
```

### JSON 格式

```json
[
  {
    "case_name": "创建用户",
    "method": "POST",
    "url": "/api/user",
    "json": {"name": "test", "age": 20},
    "expect": {"status_code": 200}
  }
]
```

### CSV 格式

| case_name | method | url | params | json | expect |
|-----------|--------|-----|--------|------|--------|
| 查询用户 | GET | /api/user/1 | | | {"status_code": 200} |

### Excel 格式

第一行为表头，字段名与上述一致，后续每行为一条用例。

## 接口依赖编排详解

### 核心概念

| 概念 | 语法 | 说明 |
|------|------|------|
| **变量提取** | `extract` | 从接口响应中用 jsonpath 提取值，存入全局上下文 |
| **变量引用** | `${变量名}` | 在 url / headers / json / params 等任意位置引用已提取的变量 |
| **全局上下文** | `context` | 整个测试过程中共享的变量池，所有用例都能读写 |

### 工作流程

```
用例1 执行请求 → 响应 JSON → extract 提取变量存入 context
                                         ↓
用例2 读取 context → ${} 替换 → 执行请求 → extract 继续提取
                                         ↓
用例3 读取 context → ${} 替换 → 执行请求 → 断言验证
```

### 变量替换规则

- **纯变量引用**：`"${user_id}"` → 保留原始类型（如 int `123`）
- **字符串拼接**：`"Bearer ${token}"` → 字符串 `"Bearer abc123"`
- **支持嵌套**：url、headers、params、json、expect 中均可使用

### 用例文件位置

- 独立接口用例：`data/test_demo.yaml`（用 parametrize 并行执行）
- 依赖编排用例：`data/test_dependency.yaml`（串行顺序执行）

## 环境配置

编辑 `config/config.yaml`：

```yaml
# 当前使用的环境
current_env: "test"

# 各环境配置
environments:
  dev:
    base_url: "http://dev-api.example.com"
  test:
    base_url: "https://jsonplaceholder.typicode.com"
  pre:
    base_url: "https://pre-api.example.com"
  prod:
    base_url: "https://api.example.com"

# 请求配置
request:
  timeout: 30          # 请求超时（秒）
  retry_count: 3       # 失败重试次数
  retry_interval: 1    # 重试间隔（秒）
  verify_ssl: false    # 是否验证 SSL 证书

# 日志配置
logging:
  level: "DEBUG"       # DEBUG=全部细节 / INFO=仅关键信息
```

运行时通过 `--env` 参数切换环境，或设置环境变量 `API_TEST_ENV`。

## 日志说明

### 日志格式

```
时间戳 [级别] 模块名 - [唯一Key] 内容
```

### 示例

```log
2026-05-27 16:03:16 [INFO]  utils.http_client - [R-2358] >>> [GET] https://xxx/posts (attempt 1)
2026-05-27 16:03:16 [DEBUG] utils.http_client - [R-2358]     Params: {'_limit': 1}
2026-05-27 16:03:17 [INFO]  utils.http_client - [R-2358] <<< [200] https://xxx/posts?_limit=1 (0.594s)
2026-05-27 16:03:17 [DEBUG] utils.http_client - [R-2358]     Response: [{'userId': 1, ...}]
2026-05-27 16:03:17 [INFO]  utils.variable_parser - 提取变量: post_id = 1 (from $[0].id)
```

### 唯一 Key 排查

每次请求都有 `[R-xxxx]` 唯一标识，搜索即可找到完整请求链路：

```bash
grep "R-2358" logs/2026-05-27.log
```

### 级别说明

| 级别 | 内容 | 适用场景 |
|------|------|----------|
| **INFO** | 请求发出、状态码、耗时、变量提取 | 日常运行 |
| **DEBUG** | 请求参数、请求体、完整响应体 | 排查问题 |

## 常用命令速查

```bash
# 运行全部用例
python3 run.py

# 运行指定文件
python3 -m pytest testcases/test_demo.py -v

# 运行指定用例
python3 -m pytest testcases/test_demo.py::test_dependency_chain -v

# 按关键词筛选
python3 -m pytest -k "yaml" -v

# 生成 HTML 报告
python3 -m pytest testcases/ --html=reports/report.html

# 生成 Allure 报告
python3 -m pytest testcases/ --alluredir=reports/allure-results
allure serve reports/allure-results
```
