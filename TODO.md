# 框架完善待办事项

## 待完成

### HTTP 客户端增强 (`utils/http_client.py`)
- [ ] 添加请求超时后的友好错误信息
- [ ] 添加请求日志的脱敏处理（密码、token 等敏感字段）

### 数据加载器增强 (`utils/data_loader.py`)
- [ ] 添加对空文件的处理（返回空列表并记录警告）
- [ ] 添加对文件编码的自动检测

### 新增功能
- [ ] 接口响应时间断言功能
- [ ] 接口幂等性测试功能
- [ ] 接口性能测试功能

### Agent 后续增强
- [ ] Agent Web 界面（Gradio/Streamlit），支持前端拖拽上传文件 + 输入测试指令
- [ ] Agent 长期记忆（历史用例经验库）
- [ ] Agent 自主生成测试用例（从 API 文档）
- [ ] Agent 钉钉机器人接入

## 已完成

- [x] AI Agent 能力接入（自然语言驱动测试）— v2.0.0
- [x] Agent API 服务（FastAPI + Gunicorn）— v2.1.0
- [x] Agent 流式响应（SSE）— v2.1.0
- [x] Agent 测试报告生成（HTML + JSON）— v2.2.0
- [x] Agent 文件上传能力 — v2.3.0
- [x] 报告增加请求/响应详情 — v2.3.1
