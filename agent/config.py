"""
Agent 专属配置

管理 LLM 模型选择、温度参数、最大循环轮次、安全限制等。
所有敏感信息从 .env 文件读取。
"""
import os

from dotenv import load_dotenv

# 加载 .env
load_dotenv()


# ==================== LLM 配置 ====================

AGENT_API_KEY: str = os.environ.get("AGENT_API_KEY", "")
AGENT_BASE_URL: str = os.environ.get("AGENT_BASE_URL", "https://api.meai.cloud")
AGENT_MODEL: str = os.environ.get("AGENT_MODEL", "claude-opus-4-7")
AGENT_TEMPERATURE: float = float(os.environ.get("AGENT_TEMPERATURE", "0.1"))

# ==================== Agent 行为配置 ====================

# 单次任务最大 ReAct 循环轮次（防止死循环）
MAX_ITERATIONS: int = 15

# 单次任务最多发送的 HTTP 请求数
MAX_REQUESTS_PER_TASK: int = 30

# 工具调用超时时间（秒）
TOOL_TIMEOUT: int = 30

# 响应体最大返回长度（超过则截断，防止超 token）
MAX_RESPONSE_LENGTH: int = 3000

# ==================== 安全配置 ====================

# Agent 权限等级（1=可执行测试, 2=可写数据, 3=完全自主）
PERMISSION_LEVEL: int = 1

# 允许请求的环境（禁止 prod 的写操作）
ALLOWED_WRITE_ENVS: list = ["dev", "test", "pre"]

# 是否需要确认写操作（POST/PUT/DELETE）
CONFIRM_WRITE_OPERATIONS: bool = False
