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

COPY alembic.ini ./
COPY migrations ./migrations
COPY docs ./docs
COPY services ./services

USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "services.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
