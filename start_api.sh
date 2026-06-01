#!/bin/bash
# Agent API 服务启动脚本
# 使用 Gunicorn + UvicornWorker 多进程启动

set -e

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

# 加载环境变量
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# 检查 API_KEY 是否配置
if [ -z "$API_KEY" ]; then
    echo "⚠️  警告: API_KEY 未配置，API 将跳过认证"
fi

# 检查 Agent API Key 是否配置
if [ -z "$AGENT_API_KEY" ]; then
    echo "❌ 错误: AGENT_API_KEY 未配置，请在 .env 中设置"
    exit 1
fi

# 启动参数
WORKERS=${WORKERS:-4}
HOST=${HOST:-0.0.0.0}
PORT=${PORT:-8000}

echo "=========================================="
echo "  🤖 API 测试 Agent 服务"
echo "=========================================="
echo "  工作进程数: $WORKERS"
echo "  监听地址: $HOST:$PORT"
echo "  模型: ${AGENT_MODEL:-claude-opus-4-7}"
echo "  环境: ${API_TEST_ENV:-test}"
echo "=========================================="

# 启动 Gunicorn
exec gunicorn \
    -w "$WORKERS" \
    -k uvicorn.workers.UvicornWorker \
    -b "$HOST:$PORT" \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    agent_api:app
