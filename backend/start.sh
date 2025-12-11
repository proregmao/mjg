#!/bin/bash
# 后端启动脚本

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 加载环境变量
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# 设置默认值
BACKEND_PORT=${BACKEND_PORT:-8087}
BACKEND_HOST=${BACKEND_HOST:-0.0.0.0}

# 激活虚拟环境
source venv/bin/activate

# 设置错误处理
set -e

# 启动uvicorn服务器，使用环境变量配置端口
# 使用 --log-level info 确保日志正常输出
exec uvicorn app.main:app --host ${BACKEND_HOST} --port ${BACKEND_PORT} --log-level info

