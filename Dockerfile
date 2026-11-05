FROM node:22-alpine AS frontend-build

WORKDIR /frontend
COPY frontend/package.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY --from=frontend-build /frontend/dist ./frontend_dist

RUN mkdir -p /data/media/videos /data/media/thumbnails

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]


FROM runtime AS test

ENV DATABASE_URL=sqlite+pysqlite:////tmp/tubeclone-test.db \
    SEED_DEMO=false \
    MEDIA_DIR=/tmp/media \
    FRONTEND_DIST=/tmp/frontend \
    JWT_SECRET=test-secret \
    COOKIE_SECURE=false \
    PYTHONPATH=/app

COPY backend/requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY backend/tests ./tests
COPY backend/pytest.ini ./pytest.ini

CMD ["python", "-m", "pytest", "-q", "tests"]


# Финальная стадия по умолчанию: обычный runtime, а не тестовый образ.
FROM runtime AS app
