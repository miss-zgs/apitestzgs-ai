# 更新日志

## v2.5.0（2026-06-11）

**前端交互页面 + 文件上传**

- **web/index.html**：新增 Agent 前端交互页面，深色主题，支持对话式交互
- **SSE 流式输出**：对接 `/chat-stream` 接口，实时展示 Agent 思考过程
- **文件上传**：输入框左侧 📎 按钮支持上传文件到 `data/` 目录，带上传进度和状态提示
- **文件管理侧边栏**：📂 按钮打开文件管理面板，支持查看、使用、删除 `data/` 目录文件
- **快捷指令**：首页提供常用操作按钮（查看数据文件、执行用例、快速测试、查看配置）
- **工具集侧边栏**：可查看 Agent 可用的 12 个工具及说明
- **状态指示**：顶部实时显示 Agent 连接状态、环境、模型信息
- **agent_api.py**：新增 `/web`（前端页面）、`/upload`（文件上传）、`/files`（文件列表）、`DELETE /files/{name}`（删除文件）接口
- **python-multipart**：新增依赖，FastAPI 文件上传支持

## v2.4.0（2026-06-11）

**项目瘦身 + 报告文件名优化**

- **报告命名**：报告文件名从 `report_时间戳` 改为 `任务名称_时间戳`（如 `认证模块接口测试报告_20260611_152700.html`），便于区分不同任务
- **项目瘦身**：移除 Pytest 模式遗留的 11 个文件（`utils/assertion.py`、`case_executor.py`、`context.py`、`bug_reporter.py`、`api/`、`testcases/`、`run.py`、`example_usage.py`、`pytest.ini`、`BUGFIX.md`），项目只保留 Agent 相关代码
- **README 更新**：全面清理 Pytest 残留描述，项目定位调整为 AI Agent 测试框架
- **TODO 清理**：移除已删模块相关的待办项，保留有效待办

## v2.3.1（2026-06-11）

**报告增加请求/响应详情 + README 补充 Agent 文档**

- **report_tool**：每个用例详情新增「查看请求/响应」折叠区域，展示完整的请求头、请求体和响应体
- **HTML 样式**：请求/响应左右分栏展示，深色代码块，支持点击折叠/展开，不影响原有布局
- **数据结构**：cases 新增 `request_body`、`response_body`、`request_headers` 三个字段
- **Prompt 优化**：提示 Agent 在每次请求后记录请求体和响应体，生成报告时必须填入
- **README**：新增 AI Agent 模式完整文档，包含启动方式（CLI/API/代码调用）、环境配置、用例格式兼容说明、报告说明；更新项目结构，补充 Agent 模块目录

## v2.3.0（2026-06-11）

**文件上传能力**

- **上传工具**：新增 `agent/tools/upload_tool.py`，Agent 可将 `data/` 目录下的文件通过 multipart/form-data 上传到指定接口
- **文件列表**：提供 `list_uploadable_files` 工具，列出 `data/` 目录下可上传的文件及大小
- **安全限制**：路径穿越防护、文件类型白名单（图片/文档/数据/压缩包等）、50MB 大小限制
- **Prompt 更新**：工作流程新增文件上传能力说明，Agent 可识别用户上传意图并调用工具

## v2.2.0（2026-06-11）

**测试报告生成能力**

- **报告工具**：新增 `agent/tools/report_tool.py`，Agent 测试完成后自动生成 HTML + JSON 双格式报告到 `reports/` 目录
- **HTML 报告**：包含通过率卡片、用例汇总表格、逐条断言详情，界面美观，开箱即用
- **JSON 报告**：结构化数据，方便程序化消费（CI/CD 集成、钉钉通知等）
- **Prompt 优化**：工作流程新增第 7 步"生成报告"，Agent 测试完成后会主动调用报告工具

## v2.1.1（2026-06-11）

**部署加固 + 安全优化**

- **依赖补全**：requirements.txt 补充 `fastapi`、`uvicorn`、`gunicorn`，所有依赖添加版本上界防止不兼容升级
- **启动脚本优化**：start_api.sh 支持 `start/stop/restart/status` 命令，新增 PID 文件管理、graceful shutdown、日志写入文件、动态计算 workers 数
- **CORS 支持**：agent_api.py 新增 CORS 中间件，支持通过 `CORS_ORIGINS` 环境变量配置允许的来源
- **输入验证**：消息长度限制 1~4000 字符，防止 token 溢出
- **对话历史修复**：chat_stream 流式模式下正确保存 AI 回复到对话历史，修复多轮对话上下文丢失问题
- **线程安全**：http_tool 请求计数器使用 `threading.Lock` 保护，避免多进程竞态
- **代码清理**：移除未使用的 `AsyncGenerator` 导入

## v2.1.0（2026-06-09）

**Agent API 服务 + 流式响应 + 体验优化**

- **API 服务**：新增 `agent_api.py`，基于 FastAPI 提供 RESTful API，支持 Gunicorn 多进程部署
  - `POST /chat` — 同步对话接口（120s 超时）
  - `POST /chat-stream` — SSE 流式响应接口，实时返回 Agent 执行进度
  - `GET /` — 健康检查
- **流式响应**：`agent/core.py` 新增 `chat_stream` 方法，基于 LangGraph `stream` 同步生成器实现
- **启动脚本**：新增 `start_api.sh`，一键启动 Gunicorn + Uvicorn Worker（4 进程）
- **响应体优化**：`MAX_RESPONSE_LENGTH` 从 3000 增加到 10000，支持更复杂的断言场景
- **断言优化**：`check_json_not_empty` 失败时返回响应体片段，便于定位问题
- **依赖新增**：`fastapi`、`uvicorn`、`gunicorn`

## v2.0.0（2026-06-01）

**AI Agent 能力接入 — 自然语言驱动接口测试**

- **Agent 核心**：新增 `agent/core.py`，基于 LangGraph ReAct 模式实现 Agent 主循环，支持多轮对话、自主规划、工具调用
- **LLM 接入**：通过 `langchain-anthropic` 接入 Claude 模型（支持中转站），配置在 `.env` 中管理
- **工具封装**：将现有 `utils/` 模块封装为 Agent 可调用的 Tool
  - `send_http_request` — HTTP 请求（含请求数限制、响应截断）
  - `check_status_code` / `check_json_field` / `check_json_contains` / `check_json_not_empty` — 断言工具
  - `extract_json_value` — JSONPath 字段提取
  - `load_test_cases` / `list_test_data_files` — 数据驱动
  - `read_project_file` — 项目文件读取（带安全白名单）
- **System Prompt**：专业 API 测试工程师角色，内置失败分析指南和安全约束
- **命令行入口**：`agent_run.py` 提供交互式 CLI（`/status` / `/clear` / `/help` / `/quit`）
- **安全设计**：请求数限制（30次/任务）、迭代次数限制（15轮）、文件读取白名单、环境隔离
- **依赖新增**：`langchain`、`langchain-anthropic`、`langgraph`、`pydantic`

## v1.1.0（2026-05-27）

**接口依赖编排 + 变量提取替换 & 工程优化**

- **用例执行引擎**：新增 `utils/case_executor.py`，抽离通用执行逻辑（`execute_case` / `execute_chain` / `parse_csv_case`），测试文件只需一行调用
- **飞猪接口接入**：新增接机查价 + 创单用例（`data/test_fliggy_pickup.yaml`），完整串行链路：查价 → 提取报价编码 → 创单
- **环境变量管理**：通过 `.env` 文件管理敏感信息（clientId / clientSecret），新增 `.env.example` 模板，新电脑 `cp .env.example .env` 填值即用
- **模块合并优化**：`context.py` + `variable_parser.py` 合并为 `context.py`，减少文件数，降低理解成本
- **数据加载日志开关**：`config.yaml` 新增 `show_data_loader` 配置，控制加载日志显示/隐藏
- **请求唯一 Key 恢复**：修复 `[R-xxxx]` 唯一请求标识丢失的问题
- **Git 规范化**：从仓库中移除 `.idea/` IDE 配置目录

## v1.0.0（2026-05-26）

**框架基础搭建**

- 统一 HTTP 请求封装（GET/POST/PUT/DELETE/PATCH/上传），自动重试、日志记录、Session 管理
- 多格式数据驱动（YAML / JSON / Excel / CSV），自动识别加载
- 通用断言工具（状态码 / jsonpath / 包含 / 类型 / 非空）
- 多环境切换（dev / test / pre / prod），通过 config.yaml 一键切换
- 全局上下文 + `${变量名}` 语法替换，支持接口间变量传递
- 日志双输出（控制台 + 按天切分文件），每次请求带唯一标识 `[R-xxxx]`
- Allure 报告支持
