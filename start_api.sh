#!/bin/bash
# Agent API 服务启动脚本
# 使用 Gunicorn + UvicornWorker 多进程启动
# 支持 start / stop / restart / status 命令

set -e

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

# PID 文件和日志目录
PID_FILE="$PROJECT_ROOT/.gunicorn.pid"
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"

# 加载环境变量
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# 启动参数
WORKERS=${WORKERS:-$(python3 -c "import os; print(min(os.cpu_count() * 2 + 1, 8))" 2>/dev/null || echo 4)}
HOST=${HOST:-0.0.0.0}
PORT=${PORT:-8002}
TIMEOUT=${GUNICORN_TIMEOUT:-120}
GRACEFUL_TIMEOUT=${GRACEFUL_TIMEOUT:-30}

start_server() {
    # 检查是否已在运行
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "⚠️  服务已在运行 (PID: $(cat "$PID_FILE"))"
        return 1
    fi

    # 检查 Agent API Key 是否配置
    if [ -z "$AGENT_API_KEY" ]; then
        echo "❌ 错误: AGENT_API_KEY 未配置，请在 .env 中设置"
        exit 1
    fi

    # 检查 API_KEY 是否配置
    if [ -z "$API_KEY" ]; then
        echo "⚠️  警告: API_KEY 未配置，API 将跳过认证"
    fi

    echo "=========================================="
    echo "  🤖 API 测试 Agent 服务"
    echo "=========================================="
    echo "  工作进程数: $WORKERS"
    echo "  监听地址: $HOST:$PORT"
    echo "  模型: ${AGENT_MODEL:-claude-opus-4-7}"
    echo "  环境: ${API_TEST_ENV:-test}"
    echo "  超时: ${TIMEOUT}s"
    echo "  PID 文件: $PID_FILE"
    echo "=========================================="

    # 启动 Gunicorn
    exec python3 -m gunicorn \
        -w "$WORKERS" \
        -k uvicorn.workers.UvicornWorker \
        -b "$HOST:$PORT" \
        --timeout "$TIMEOUT" \
        --graceful-timeout "$GRACEFUL_TIMEOUT" \
        --pid "$PID_FILE" \
        --access-logfile "$LOG_DIR/access.log" \
        --error-logfile "$LOG_DIR/error.log" \
        --capture-output \
        agent_api:app
}

stop_server() {
    if [ ! -f "$PID_FILE" ]; then
        echo "⚠️  PID 文件不存在，尝试通过端口查找..."
        local pid
        pid=$(lsof -ti:"$PORT" 2>/dev/null | head -1)
        if [ -n "$pid" ]; then
            echo "🛑 正在停止服务 (PID: $pid)..."
            kill -TERM "$pid" 2>/dev/null
            sleep 2
            kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null
            echo "✅ 服务已停止"
        else
            echo "ℹ️  服务未运行"
        fi
        return 0
    fi

    local pid
    pid=$(cat "$PID_FILE")
    if kill -0 "$pid" 2>/dev/null; then
        echo "🛑 正在优雅停止服务 (PID: $pid)..."
        kill -TERM "$pid"
        # 等待进程退出（最多等 graceful timeout + 5 秒）
        local wait_count=0
        local max_wait=$((GRACEFUL_TIMEOUT + 5))
        while kill -0 "$pid" 2>/dev/null && [ $wait_count -lt $max_wait ]; do
            sleep 1
            wait_count=$((wait_count + 1))
        done
        # 如果还没退出，强制杀掉
        if kill -0 "$pid" 2>/dev/null; then
            echo "⚠️  优雅停止超时，强制终止..."
            kill -9 "$pid" 2>/dev/null
        fi
        rm -f "$PID_FILE"
        echo "✅ 服务已停止"
    else
        echo "ℹ️  服务未运行（清理过期 PID 文件）"
        rm -f "$PID_FILE"
    fi
}

status_server() {
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "✅ 服务运行中 (PID: $(cat "$PID_FILE"))"
        # 健康检查
        if curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$PORT/" | grep -q "200"; then
            echo "✅ 健康检查通过"
        else
            echo "⚠️  健康检查失败"
        fi
    else
        echo "❌ 服务未运行"
    fi
}

# 命令分发
case "${1:-start}" in
    start)
        start_server
        ;;
    stop)
        stop_server
        ;;
    restart)
        stop_server
        sleep 2
        start_server
        ;;
    status)
        status_server
        ;;
    *)
        echo "用法: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
