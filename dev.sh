#!/usr/bin/env bash
# Shred 开发模式(无 Docker):后端热重载 + 前端热更新
# 浏览器打开 http://localhost:5173
set -e
cd "$(dirname "$0")"

PYTHON=".venv/Scripts/python.exe"

if [ ! -x "$PYTHON" ]; then
  echo "→ 创建虚拟环境并安装依赖..."
  python -m venv .venv
  "$PYTHON" -m pip install -e ".[dev]" \
    --trusted-host pypi.org --trusted-host files.pythonhosted.org
fi

if [ ! -d frontend/node_modules ]; then
  echo "→ 安装前端依赖..."
  (cd frontend && npm ci)
fi

mkdir -p data
SHRED_DATA_DIR=./data "$PYTHON" -m alembic upgrade head

echo "→ 后端 http://localhost:8000 (代码改动自动重载)"
echo "→ 前端 http://localhost:5173 (代码改动自动刷新)"
echo "  (Ctrl+C 同时停止两者)"

SHRED_DATA_DIR=./data "$PYTHON" -m uvicorn shred.main:app \
  --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!

(cd frontend && npx vite --port 5173) &
FRONTEND_PID=$!

trap 'kill $BACKEND_PID $FRONTEND_PID 2>/dev/null' EXIT
wait
