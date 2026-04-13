#!/bin/sh
set -e

if [ "$SERVICE_ROLE" = "worker" ]; then
    exec celery -A tasks.celery_app worker --beat --loglevel=info --concurrency=2
else
    exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 2 --loop uvloop
fi
