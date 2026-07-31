FROM node:20-bookworm-slim AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


FROM python:3.12-slim AS runtime

ARG RAILWAY_SERVICE_NAME

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Tashkent

WORKDIR /app

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends ffmpeg tzdata \
    && if [ "$RAILWAY_SERVICE_NAME" = "curriculum-worker" ]; then \
        DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
            libreoffice-core \
            libreoffice-impress \
            poppler-utils \
            fonts-dejavu-core \
            fonts-liberation; \
    fi \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini config.py main.py ./
COPY backend ./backend
COPY database ./database
COPY scripts ./scripts
COPY tgbot ./tgbot
COPY --from=frontend-builder /app/backend/static/react /app/backend/static/react
RUN python -c "from backend.core.web.assets import ensure_js_bundles; ensure_js_bundles('backend/static')"
RUN chmod +x scripts/railway_start.sh

EXPOSE 8080

CMD ["python", "main.py", "web"]
