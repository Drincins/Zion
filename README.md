# Zion
Внутреннее web-приложение на `FastAPI + PostgreSQL + Vue 3 (Vite)`.


## Что в проекте
- backend: `FastAPI` (порт `8000`)
- db: `PostgreSQL 16` в Docker (`db`)
- frontend: `Vue 3 + Vite` (`frontend/`)


## Обновление на сервере
```bash
git pull
docker compose up -d --build
```


## Быстрый старт (локально)
Все команды выполнять из корня проекта, где лежит `docker-compose.yml`.

### Вариант 1: поднять все в Docker
```bash
docker compose up --build
```
Приложение будет доступно на `http://127.0.0.1:8000` или `http://localhost:8000`.
Важно: в этом режиме frontend собран статически, без Vite hot reload.

### Вариант 2: разработка frontend с hot reload
Терминал 1:
```bash
docker compose up -d db backend
```

Терминал 2:
```bash
cd frontend
npm ci
npm run dev
```
Открыть: `http://127.0.0.1:5173` или `http://localhost:5173`.
Изменения во `frontend/src` применяются сразу, без перезапуска.


## Обновить локальную БД из дампа сервера
1. На сервере перейти в каталог проекта, например `cd /opt/Zion`.
2. Убедиться, что БД запущена: `docker compose up -d db`.
3. Сделать дамп: `docker compose exec db pg_dump -U zion_user -d zion > db.sql`.
4. Скопировать `db.sql` на локальный ПК в корень проекта.
5. На локалке — полностью удалить старую БД `docker compose down -v`
6. Закинуть файл db.sql в папку проекта
7. Поднять только postgres `docker compose up -d db`
8. Скопировать дамп в контейнер `docker compose cp db.sql db:/db.sql`
9. Восстановить дамп В БАЗУ:
Войти в контейнер `docker compose exec -it db bash`
10. Применить дамп `psql -U zion_user -d zion -f /db.sql`
