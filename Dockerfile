FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg nodejs npm \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY web/frontend/package*.json web/frontend/
RUN cd web/frontend && npm ci

COPY . .
RUN cd web/frontend && npm run build
RUN chmod +x scripts/railway_start.sh

EXPOSE 8080

CMD ["sh", "-c", "uvicorn web.backend.server:app --host 0.0.0.0 --port ${PORT:-8080}"]
