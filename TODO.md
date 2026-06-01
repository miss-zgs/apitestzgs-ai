# 框架完善待办事项

## 2026-06-01

### 断言工具增强 (`utils/assertion.py`)
- [x] 在 `assert_by_expect` 中添加 `contains` 断言类型支持
- [x] 在 `assert_by_expect` 中添加 `type` 断言类型支持
- [x] 在 `assert_by_expect` 中添加 `not_empty` 断言类型支持

### HTTP 客户端增强 (`utils/http_client.py`)
- [ ] 添加请求超时后的友好错误信息
- [ ] 添加请求日志的脱敏处理（密码、token 等敏感字段）

### 数据加载器增强 (`utils/data_loader.py`)
- [ ] 添加对空文件的处理（返回空列表并记录警告）
- [ ] 添加对文件编码的自动检测

### Bug 报告工具增强 (`utils/bug_reporter.py`)
- [ ] 添加 `get_bug_statistics()` 统计功能
- [ ] 添加 `export_bugs_to_csv()` 导出功能

### 配置文件增强 (`config/config.yaml`)
- [ ] 添加 `assertion` 配置项（strict_mode、ignore_fields）
- [ ] 添加 `bug` 配置项（auto_report、sensitive_fields）

### 新增功能
- [x] AI Agent 能力接入（自然语言驱动测试）— v2.0.0 完成
- [ ] 接口响应时间断言功能
- [ ] 接口幂等性测试功能
- [ ] 接口性能测试功能

### Agent 后续增强
- [ ] Agent Web 界面（Gradio/Streamlit）
- [ ] Agent 长期记忆（历史用例经验库）
- [ ] Agent 自主生成测试用例（从 API 文档）
- [ ] Agent 钉钉机器人接入
