FROM python:3.12.10-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN groupadd --system --gid 10001 evalpulse \
    && useradd --system --uid 10001 --gid evalpulse --home-dir /app evalpulse

WORKDIR /app
COPY pyproject.toml README.md ./
COPY python ./python
RUN pip install --no-cache-dir .

COPY services ./services

USER 10001:10001
CMD ["celery", "-A", "evalpulse.tasks:celery_app", "worker", "--beat", "--schedule=/tmp/celerybeat-schedule", "--loglevel=INFO", "--concurrency=2"]
