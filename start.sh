#!/usr/bin/env bash
# Shred 一键启动(无 Docker)
# 用法:
#   ./start.sh           启动(前端未构建时自动构建)
#   ./start.sh --build   强制重新构建前端后启动
set -e
cd "$(dirname "$0")"

PYTHON=".venv/Scripts/python.exe"
PORT="${SHRED_PORT:-9400}"

# ---------- 首次初始化:虚拟环境 ----------
if [ ! -x "$PYTHON" ]; then
  echo "→ 创建虚拟环境并安装依赖..."
  python -m venv .venv
  "$PYTHON" -m pip install -e ".[dev]" \
    --trusted-host pypi.org --trusted-host files.pythonhosted.org
fi

# ---------- 前端构建 ----------
if [ ! -d frontend/dist ] || [ "$1" = "--build" ]; then
  echo "→ 构建前端..."
  (cd frontend && npm ci && npm run build)
fi

# ---------- 静态文件与数据 ----------
mkdir -p static data
cp -r frontend/dist/* static/

echo "→ 准备数据库..."
SHRED_DATA_DIR=./data "$PYTHON" -m alembic upgrade head

# ---------- 启动 ----------
echo "→ Shred 运行在 http://localhost:${PORT}"
echo "  (Ctrl+C 停止)"
SHRED_DATA_DIR=./data "$PYTHON" -m uvicorn shred.main:app \
  --host 127.0.0.1 --port "${PORT}"
