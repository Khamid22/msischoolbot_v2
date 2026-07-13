FROM node:20-bookworm-slim AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock

COPY alembic.ini config.py main.py ./
COPY backend ./backend
COPY database ./database
COPY scripts ./scripts
COPY tgbot ./tgbot
COPY --from=frontend-builder /app/backend/static/react /app/backend/static/react
RUN chmod +x scripts/railway_start.sh

EXPOSE 8080

CMD ["python", "main.py", "web"]
