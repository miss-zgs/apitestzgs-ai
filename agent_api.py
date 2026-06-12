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

from fastapi import FastAPI, HTTPException, Header, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from utils.logger import setup_logging
from agent.core import TestAgent
from config.settings import get_project_root

# 初始化日志
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="API 测试 Agent",
    description="通过自然语言驱动接口自动化测试",
    version="2.1.0",
)

# CORS 中间件 — 允许前端跨域调用
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


# 消息最大长度（防止 token 溢出）
MAX_MESSAGE_LENGTH = 4000


class ChatRequest(BaseModel):
    """对话请求"""
    message: str = Field(..., min_length=1, max_length=MAX_MESSAGE_LENGTH, description="用户消息")


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
                # SSE 规范中 data 字段不能包含裸换行，需转义
                escaped = chunk.replace('\n', '\\n')
                yield f"data: {escaped}\n\n"
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


# ==================== 文件管理接口 ====================

# 允许上传的文件扩展名
_ALLOWED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".txt", ".csv", ".json", ".yaml", ".yml", ".xml",
    ".zip", ".tar", ".gz", ".rar",
    ".mp4", ".mp3", ".wav",
}

# 最大上传文件大小：50MB
_MAX_UPLOAD_SIZE = 50 * 1024 * 1024


@app.post("/upload")
async def upload_file_to_data(
    file: UploadFile = File(...),
    x_api_key: str = Header(None),
):
    """
    上传文件到 data/ 目录

    前端将文件上传到此接口，文件会保存到 data/ 目录下，
    之后 Agent 可通过 upload_file 工具将其上传到被测接口。
    """
    if not verify_api_key(x_api_key or ""):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    # 安全：清理文件名，防止路径穿越
    safe_filename = os.path.basename(file.filename)
    if not safe_filename or safe_filename.startswith("."):
        raise HTTPException(status_code=400, detail=f"非法文件名: {file.filename}")

    # 扩展名检查
    _, extension = os.path.splitext(safe_filename)
    if extension.lower() not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {extension}，允许: {', '.join(sorted(_ALLOWED_EXTENSIONS))}",
        )

    # 读取文件内容并检查大小
    content = await file.read()
    if len(content) > _MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件过大: {len(content) / 1024 / 1024:.1f}MB，最大 {_MAX_UPLOAD_SIZE // 1024 // 1024}MB",
        )

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="文件内容为空")

    # 保存到 data/ 目录
    data_dir = os.path.join(get_project_root(), "data")
    os.makedirs(data_dir, exist_ok=True)
    save_path = os.path.join(data_dir, safe_filename)

    with open(save_path, "wb") as save_file:
        save_file.write(content)

    size_str = f"{len(content) / 1024:.1f}KB" if len(content) < 1024 * 1024 else f"{len(content) / 1024 / 1024:.1f}MB"
    logger.info("文件已上传: data/%s (%s)", safe_filename, size_str)

    return {
        "message": f"文件已上传: data/{safe_filename}",
        "filename": safe_filename,
        "size": size_str,
    }


@app.get("/files")
async def list_data_files(x_api_key: str = Header(None)):
    """列出 data/ 目录下的所有文件"""
    if not verify_api_key(x_api_key or ""):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    data_dir = os.path.join(get_project_root(), "data")
    if not os.path.isdir(data_dir):
        return {"files": []}

    files = []
    for filename in sorted(os.listdir(data_dir)):
        if filename.startswith("."):
            continue
        filepath = os.path.join(data_dir, filename)
        if os.path.isfile(filepath):
            size = os.path.getsize(filepath)
            _, ext = os.path.splitext(filename)
            size_str = f"{size / 1024:.1f}KB" if size < 1024 * 1024 else f"{size / 1024 / 1024:.1f}MB"
            files.append({"name": filename, "size": size_str, "ext": ext})

    return {"files": files}


@app.delete("/files/{filename}")
async def delete_data_file(filename: str, x_api_key: str = Header(None)):
    """删除 data/ 目录下的指定文件"""
    if not verify_api_key(x_api_key or ""):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    safe_filename = os.path.basename(filename)
    data_dir = os.path.join(get_project_root(), "data")
    file_path = os.path.join(data_dir, safe_filename)

    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail=f"文件不存在: {safe_filename}")

    os.remove(file_path)
    logger.info("文件已删除: data/%s", safe_filename)
    return {"message": f"已删除: data/{safe_filename}"}


# ==================== 测试报告访问 ====================
_REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
os.makedirs(_REPORTS_DIR, exist_ok=True)


@app.get("/reports/{filename:path}")
async def serve_report(filename: str):
    """提供测试报告文件访问（支持中文文件名）"""
    from urllib.parse import unquote
    decoded_name = unquote(filename)
    file_path = os.path.join(_REPORTS_DIR, decoded_name)
    if not os.path.abspath(file_path).startswith(os.path.abspath(_REPORTS_DIR)):
        raise HTTPException(status_code=403, detail="禁止访问")
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="报告不存在")
    media_type = "text/html" if file_path.endswith(".html") else "application/json"
    return FileResponse(file_path, media_type=media_type)


# ==================== 启动入口 ====================

# 前端页面路由
_WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")


@app.get("/web")
async def web_ui():
    """前端交互页面（动态注入 API_KEY）"""
    index_path = os.path.join(_WEB_DIR, "index.html")
    if not os.path.isfile(index_path):
        raise HTTPException(status_code=404, detail="前端页面未找到")

    with open(index_path, "r", encoding="utf-8") as html_file:
        html_content = html_file.read()

    # 将 .env 中的 API_KEY 动态注入到前端 JS
    api_key = os.environ.get("API_KEY", "")
    html_content = html_content.replace(
        "const API_KEY = '';",
        f"const API_KEY = '{api_key}';",
    )

    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html_content)


# 挂载静态资源（放在所有路由之后，避免拦截 API 路径）
if os.path.isdir(_WEB_DIR):
    app.mount("/static", StaticFiles(directory=_WEB_DIR), name="static")

# 挂载 reports 目录，让用户可以通过浏览器直接查看测试报告
_REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
os.makedirs(_REPORTS_DIR, exist_ok=True)
app.mount("/reports", StaticFiles(directory=_REPORTS_DIR, html=True), name="reports")


if __name__ == "__main__":
    import uvicorn

    logger.info("启动 Agent API 服务...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8002,
        log_level="info",
    )
