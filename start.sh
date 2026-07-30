#!/bin/bash
# ============================================
# 🎫 演唱会票务监控系统 - 启动脚本
# ============================================

set -e

echo "============================================"
echo "    🎫 演唱会票务监控系统 - 启动脚本"
echo "============================================"
echo ""

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到 Python3，请先安装 Python 3.12+"
    exit 1
fi

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "[警告] 未找到 Node.js，前端将无法启动"
fi

echo "[1/4] 检查后端依赖..."
cd "$PROJECT_DIR/backend"

if [ ! -d "venv" ]; then
    echo "[信息] 创建 Python 虚拟环境..."
    python3 -m venv venv
fi

source venv/bin/activate

echo "[2/4] 安装 Python 依赖..."
pip install -r requirements.txt -q

echo "[3/4] 初始化数据库..."
python init_db.py

echo "[4/4] 启动服务..."
echo ""
echo "后端 API:  http://localhost:8000"
echo "API 文档: http://localhost:8000/docs"
echo "前端页面: http://localhost:5173"
echo ""
echo "按 Ctrl+C 停止服务"
echo "============================================"

# 启动后端（后台）
cd "$PROJECT_DIR/backend"
python run.py &
BACKEND_PID=$!

# 启动前端（后台）
cd "$PROJECT_DIR/frontend"
npm install --silent
npm run dev &
FRONTEND_PID=$!

# 等待信号
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM
wait
