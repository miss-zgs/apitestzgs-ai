"""
Agent API 服务

使用 FastAPI 提供 RESTful API，让其他系统可以调用 Agent。

启动:
    python3 agent_api.py

API 端点:
    POST /chat      - 与 Agent 对话
    GET  /status    - 查看 Agent 状态
    POST /clear     - 清空对话历史
"""
import logging
import os
import time
from asyncio import Semaphore

from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from utils.logger import setup_logging
from agent.core import TestAgent

# 初始化日志
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="API 测试 Agent",
    description="通过自然语言驱动接口自动化测试",
    version="1.0.0",
)

# 全局 Agent 实例
agent: TestAgent = None

# 并发控制：限制最多 3 个并发请求
request_semaphore = Semaphore(3)


def get_agent() -> TestAgent:
    """获取 Agent 实例（懒加载）"""
    global agent
    if agent is None:
        agent = TestAgent()
        _ = agent.graph  # 触发初始化
        logger.info("Agent 已初始化")
    return agent


def verify_api_key(x_api_key: str) -> bool:
    """验证 API Key"""
    expected_key = os.environ.get("API_KEY")
    if not expected_key:
        logger.warning("API_KEY 未配置，跳过认证")
        return True
    return x_api_key == expected_key


# ==================== 请求/响应模型 ====================


class ChatRequest(BaseModel):
    """对话请求"""
    message: str


class ChatResponse(BaseModel):
    """对话响应"""
    response: str
    success: bool = True


class StatusResponse(BaseModel):
    """状态响应"""
    model: str
    env: str
    base_url: str
    conversation_rounds: int
    request_count: int
    max_iterations: int


# ==================== API 端点 ====================


@app.on_event("startup")
async def startup_event():
    """启动时初始化 Agent"""
    logger.info("Agent API 服务启动中...")
    get_agent()
    logger.info("Agent API 服务已启动")


@app.get("/")
async def root():
    """健康检查"""
    return {"status": "ok", "service": "API 测试 Agent"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, x_api_key: str = Header(None)):
    """
    与 Agent 对话

    发送自然语言描述，Agent 会自动规划并执行测试。

    请求头:
        X-API-Key: API 密钥（从环境变量 API_KEY 读取）
    """
    # 认证检查
    if not verify_api_key(x_api_key or ""):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    # 并发控制
    async with request_semaphore:
        start_time = time.time()
        try:
            agent = get_agent()
            # 增加超时时间，支持更复杂的测试场景
            response = agent.chat(request.message, timeout=120)
            duration = time.time() - start_time
            logger.info(
                "Chat request: %s... duration=%.1fs",
                request.message[:50],
                duration,
            )
            return ChatResponse(response=response, success=True)
        except Exception as exc:
            duration = time.time() - start_time
            logger.error(
                "Chat request failed: %s (duration=%.1fs)",
                exc,
                duration,
                exc_info=True,
            )
            return ChatResponse(response=f"Agent 执行失败: {exc}", success=False)


@app.get("/status", response_model=StatusResponse)
async def status(x_api_key: str = Header(None)):
    """获取 Agent 当前状态"""
    # 认证检查
    if not verify_api_key(x_api_key or ""):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    
    agent = get_agent()
    status_text = agent.get_status()
    
    # 解析状态文本
    result = {}
    for line in status_text.split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip()
    
    return StatusResponse(
        model=result.get("模型", ""),
        env=result.get("环境", ""),
        base_url=result.get("Base URL", ""),
        conversation_rounds=int(result.get("对话轮次", 0)),
        request_count=int(result.get("本轮请求数", 0).split("/")[0]),
        max_iterations=int(result.get("最大迭代", 0)),
    )


@app.post("/clear")
async def clear(x_api_key: str = Header(None)):
    """清空对话历史"""
    # 认证检查
    if not verify_api_key(x_api_key or ""):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    
    agent = get_agent()
    agent.clear_history()
    logger.info("对话历史已清空")
    return {"message": "对话历史已清空"}


@app.get("/tools")
async def list_tools(x_api_key: str = Header(None)):
    """列出所有可用工具"""
    # 认证检查
    if not verify_api_key(x_api_key or ""):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    
    from agent.core import ALL_TOOLS
    return {
        "tools": [
            {
                "name": tool.name,
                "description": tool.description,
            }
            for tool in ALL_TOOLS
        ]
    }


@app.post("/chat-stream")
async def chat_stream(request: ChatRequest, x_api_key: str = Header(None)):
    """
    与 Agent 流式对话（SSE）

    发送自然语言描述，Agent 会流式返回每一步结果。
    适合需要实时看到进度的场景。

    请求头:
        X-API-Key: API 密钥（从环境变量 API_KEY 读取）
    
    响应格式:
        text/event-stream (SSE)
    """
    # 认证检查
    if not verify_api_key(x_api_key or ""):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    def generate():
        """生成 SSE 数据流（同步生成器）"""
        try:
            agent = get_agent()
            for chunk in agent.chat_stream(request.message):
                # SSE 格式: data: <content>\n\n
                yield f"data: {chunk}\n\n"
            # 发送结束标记
            yield "data: [DONE]\n\n"
        except Exception as exc:
            logger.error("Stream chat failed: %s", exc, exc_info=True)
            yield f"data: 错误: {exc}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
        },
    )


# ==================== 启动入口 ====================


if __name__ == "__main__":
    import uvicorn
    
    logger.info("启动 Agent API 服务...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
