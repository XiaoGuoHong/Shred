#!/bin/sh
set -e

cd /app

if [ -f /data/shred.db ]; then
  echo "Running database migrations..."
  python -m alembic upgrade head
else
  echo "Fresh database — creating schema..."
  python -m alembic upgrade head
fi

exec uvicorn shred.main:app --host 0.0.0.0 --port 8000
