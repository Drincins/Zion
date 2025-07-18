# Stage 1: Build frontend
FROM node:20 AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN yarn install
COPY frontend/ .
RUN yarn build

# Stage 2: Backend
FROM python:3.13.5 AS backend

WORKDIR /app
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY .env .
COPY backend ./backend
COPY alembic ./alembic
COPY alembic.ini .

COPY --from=frontend-build /frontend/dist ./app/static

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
