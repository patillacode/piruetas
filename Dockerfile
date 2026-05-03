FROM node:22-slim AS js-builder
WORKDIR /build
COPY package.json package-lock.json* ./
RUN npm ci --ignore-scripts
COPY scripts/ scripts/
RUN node scripts/build-tiptap.mjs

FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.7 /uv /uvx /usr/local/bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app/ app/
COPY --from=js-builder /build/app/static/js/vendor/ app/static/js/vendor/

RUN addgroup --system --gid 1000 appuser && \
    adduser --system --uid 1000 --gid 1000 --no-create-home appuser && \
    mkdir -p /data/uploads && \
    chown -R appuser:appuser /app /data

LABEL org.opencontainers.image.source=https://github.com/patillacode/piruetas

USER appuser

ENV UV_NO_CACHE=1

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
