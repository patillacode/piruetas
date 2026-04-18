FROM python:3.12-slim

WORKDIR /app

RUN pip install uv --no-cache-dir

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app/ app/

RUN addgroup --system --gid 1000 appuser && \
    adduser --system --uid 1000 --gid 1000 --no-create-home appuser && \
    mkdir -p /data/uploads && \
    chown -R appuser:appuser /data

USER appuser

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
