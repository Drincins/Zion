# Stage 1: Build frontend
FROM node:20-bullseye-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm install -g npm@11.8.0
RUN npm ci
COPY frontend/ .
RUN npm run build

# Stage 2: Backend
FROM python:3.12-slim AS backend

WORKDIR /app
COPY requirements.txt .

RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
 && rm -rf /var/lib/apt/lists/* \
 && pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY backend ./backend
COPY core ./core
COPY alembic ./alembic
COPY alembic.ini .

COPY --from=frontend-build /frontend/dist ./app/static

EXPOSE 8000

CMD ["sh", "backend/entrypoint.sh"]
