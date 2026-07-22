#!/bin/sh
set -eu

celery -A evalpulse.tasks:celery_app worker \
  --beat \
  --schedule=/tmp/celerybeat-schedule \
  --loglevel=INFO \
  --concurrency=1 &

exec uvicorn services.api.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --no-access-log
