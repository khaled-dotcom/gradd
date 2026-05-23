#!/bin/sh
set -e
cd /app
exec uvicorn backend.src.main:app --host 0.0.0.0 --port "${WEBSITES_PORT:-8000}"
