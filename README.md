# API 接口自动化测试框架

基于 Python + AI Agent 的接口自动化测试框架，通过**自然语言驱动测试**，开箱即用。

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
# Agent 命令行交互模式
python3 agent_run.py

# Agent API 服务模式
python3 agent_api.py
```

---

## 核心特性

- **统一请求封装** — GET/POST/PUT/DELETE/PATCH/文件上传，自动重试、日志记录、Session 管理
- **多格式数据驱动** — 支持 YAML / JSON / Excel / CSV 四种用例格式，自动识别加载
- **AI Agent 驱动** — 自然语言描述测试需求，Agent 自动执行并生成报告
- **智能断言校验** — 状态码、jsonpath 字段值、包含/类型/非空等多种断言
- **多环境切换** — 通过配置文件一键切换 dev / test / pre / prod
- **接口依赖处理** — Agent 自动处理接口间依赖（登录获取 token → 带 token 查询）
- **请求唯一 Key** — 每次请求自动生成唯一标识 `[R-xxxx]`，日志排查一搜即达
- **日志双输出** — 控制台 + 按天切分的日志文件，支持 DEBUG/INFO 级别切换
- **测试报告** — 自动生成 HTML + JSON 双格式报告，含请求/响应详情

## AI Agent 模式（自然语言驱动测试）

本框架通过 **AI Agent** 驱动测试，用自然语言描述测试需求，Agent 自动完成用例加载、请求发送、断言校验、报告生成全流程。

### Agent 核心能力

| 能力 | 说明 |
|------|------|
| **自然语言理解** | 用中文描述测试需求，Agent 自动拆解为具体步骤 |
| **多格式用例加载** | 支持 YAML / JSON / CSV / Excel（`.xlsx`/`.xls`）四种格式 |
| **智能格式适配** | 用例字段名不必严格统一，Agent 能自动理解各种命名风格 |
| **接口依赖处理** | 自动提取 token 等变量，处理接口间的串行依赖 |
| **断言校验** | 状态码、jsonpath 字段值、包含、非空等多种断言 |
| **失败分析** | 自动分析失败原因（网络/认证/参数/服务端/断言/环境） |
| **报告生成** | 测试完成后自动生成 HTML + JSON 双格式报告，含请求/响应详情 |
| **文件上传** | 支持 multipart/form-data 文件上传测试 |

### 启动方式

#### 方式一：命令行交互模式

```bash
python3 agent_run.py
```

启动后进入交互式对话，直接输入自然语言即可：

```
👤 你: 加载 test_demo.yaml 并执行所有用例
🤖 Agent 思考中...
🤖 Agent: ✅ 已执行 3 条用例，通过率 100%...

👤 你: 测试 http://xxx.com/api/login，用 POST 发送 {"username":"admin","password":"123"}，期望 200
🤖 Agent 思考中...
🤖 Agent: ✅ 状态码 200，登录成功...
```

内置命令：

| 命令 | 说明 |
|------|------|
| `/status` | 查看 Agent 状态（模型、环境、请求数等） |
| `/clear` | 清空对话历史，开始新对话 |
| `/help` | 显示帮助 |
| `/quit` | 退出 |

#### 方式二：API 服务模式

```bash
python3 agent_api.py
# 或使用启动脚本
bash start_api.sh
```

服务启动在 `http://0.0.0.0:8002`，提供 RESTful API：

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/chat` | 与 Agent 对话（同步） |
| POST | `/chat-stream` | 与 Agent 流式对话（SSE） |
| GET | `/status` | 查看 Agent 状态 |
| POST | `/clear` | 清空对话历史 |
| GET | `/tools` | 列出所有可用工具 |

调用示例：

```bash
curl -X POST http://localhost:8002/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "加载 test_demo.yaml 执行全部用例并生成报告"}'
```

#### 方式三：代码调用

```python
from agent.core import TestAgent

agent = TestAgent()
response = agent.chat("测试 /api/users/1 接口，期望状态码 200")
print(response)
```

### Agent 环境配置

在 `.env` 文件中配置以下变量：

```bash
# LLM 配置（必填）
AGENT_API_KEY=你的API密钥
AGENT_BASE_URL=https://api.meai.cloud     # LLM 接口地址
AGENT_MODEL=claude-opus-4-7           # 模型名称
AGENT_TEMPERATURE=0.1                     # 温度参数

# API 服务认证（选填）
API_KEY=你的API服务密钥                     # 不配置则跳过认证
```

### 用例文件格式兼容

Agent 对用例文件格式有很强的**兼容性**，不要求严格统一字段名。以下格式均可被正确识别：

**标准格式**（推荐）：
```yaml
- case_name: "查询用户"
  method: GET
  url: /api/user/1
  expect:
    status_code: 200
```

**自定义格式**（同样支持）：
```yaml
config:
  base_url: "http://your-api.com"
auth_module:
  - case_id: AUTH_001
    name: "用户注册"
    request:
      method: POST
      path: /auth/register
      body: { username: "test" }
    expected:
      status_code: 200
      response: { code: 200 }
```

> Agent 基于 LLM 理解用例内容，因此字段名差异（如 `url` vs `path`、`expect` vs `expected`）不影响执行。只需在对话中简要说明格式即可。

### Agent 测试报告

测试完成后自动生成报告到 `reports/` 目录：

- **HTML 报告**：美观的可视化报告，包含通过率卡片、用例汇总表格、逐条断言详情
- **JSON 报告**：结构化数据，适合 CI/CD 集成、钉钉通知等
- **请求/响应详情**：每个用例可展开查看完整的请求头、请求体和响应体，方便排查问题

## 项目结构

```
apitestzgs-ai/
├── agent/                       → AI Agent 核心模块
│   ├── __init__.py
│   ├── core.py                  # Agent 核心（ReAct 循环、工具编排、对话管理）
│   ├── config.py                # Agent 配置（模型、温度、安全限制等）
│   ├── prompts.py               # Agent 系统提示词模板
│   └── tools/                   # Agent 工具集（6 个文件，12 个工具函数）
│       ├── __init__.py          # 模块标识
│       ├── http_tool.py         # HTTP 请求工具（send_http_request）
│       ├── assertion_tool.py    # 断言校验工具（状态码/字段值/包含/非空/提取）
│       ├── data_tool.py         # 用例数据加载工具（YAML/JSON/CSV/Excel）
│       ├── file_tool.py         # 项目文件读取工具（只读，白名单控制）
│       ├── report_tool.py       # 测试报告生成工具（HTML + JSON 双格式）
│       └── upload_tool.py       # 文件上传工具（multipart/form-data）
├── agent_run.py                 → Agent 命令行交互入口
├── agent_api.py                 → Agent API 服务入口（FastAPI）
├── start_api.sh                 → API 服务启动脚本（Gunicorn 多进程）
├── config/                      → 环境配置
│   ├── __init__.py
│   ├── config.yaml              # 环境配置（域名、超时、重试、日志级别等）
│   └── settings.py              # 配置读取工具
├── utils/                       → 基础设施层（Agent 工具的底层依赖）
│   ├── __init__.py
│   ├── http_client.py           # HTTP 请求封装（重试、唯一 Key、Session、日志）
│   ├── data_loader.py           # 多格式数据加载器（YAML/JSON/CSV/Excel）
│   └── logger.py                # 日志初始化（控制台 + 按天切分文件双输出）
├── data/                        → 用例数据文件目录
│   └── 11.yaml                  # 示例：电商 Mock API 认证模块用例
├── web/                         → 前端交互页面
│   └── index.html               # Agent 对话式 UI（深色主题，SSE 流式输出）
├── logs/                        → 日志输出目录（按天切分，自动保留 30 天）
├── reports/                     → 测试报告输出目录（HTML + JSON）
├── .env.example                 → 环境变量模板
├── requirements.txt             → Python 依赖清单
├── CHANGELOG.md                 → 版本更新日志
├── TODO.md                      → 待办事项
└── README.md                    → 项目说明文档
```

## 常用运行方式

```bash
# Agent 命令行交互模式
python3 agent_run.py

# Agent API 服务模式（启动后访问前端页面）
python3 agent_api.py
# 前端页面地址: http://localhost:8002/web

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
# Agent 命令行交互模式
python3 agent_run.py

# Agent API 服务模式
python3 agent_api.py

# 使用启动脚本
bash start_api.sh

# 查看当天日志
cat logs/$(date +%Y-%m-%d).log

# 搜索某次请求的完整链路（用唯一 Key）
grep "R-2358" logs/2026-05-27.log

# API 调用示例
curl -X POST http://localhost:8002/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "加载 data/11.yaml 执行全部用例并生成报告"}'
```
