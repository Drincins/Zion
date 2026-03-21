запустить весь проект фронт + бэк (команду запускать в корне проекта)
docker-compose up --build

на Сервере

docker compose up -d --build

Инструкция Актуализации БД
Перед выполнением команд убедитесь, что работаете из папки, где лежит `docker-compose.yml` проекта (например, `/opt/Zion`). Если нужно запускать команды из другого места, добавьте флаг `-f /полный/путь/docker-compose.yml` ко всем командам `docker compose ...`, иначе появится ошибка `no configuration file provided`.

1) Зайти на сервер и перейти в корень проекта (`cd /opt/Zion`).
2) Убедиться, что контейнер базы запущен (или поднять его):
docker compose up -d db
3) Проверить, что сервис доступен и контейнер создан (контейнер будет называться вроде `zion-db-1`):
docker compose ps db
4) Сохранить дамп (используется имя сервиса, поэтому не нужно помнить имя контейнера):
docker compose exec db pg_dump -U zion_user -d zion > db.sql
5) Проверить размер:
ls -lh db.sql
6) Скачать файл на локальный ПК:
Зайти на сервер в opt/zion/db.sql
7) На локалке — полностью удалить старую БД:
docker compose down -v
8) Закинуть файл db.sql в папку проекта
9) Поднять только postgres:
docker compose up -d db
10) Скопировать дамп в контейнер (опять же по имени сервиса):
docker compose cp db.sql db:/db.sql
11) Восстановить дамп В БАЗУ:
Войти в контейнер:
docker compose exec -it db bash
12) Применить дамп:
psql -U zion_user -d zion -f /db.sql

## Frontend (npm)

Для фронтенда используется только `npm` (lockfile: `frontend/package-lock.json`).
`yarn` для этого проекта не поддерживается.

Локальный запуск и проверка сборки:

```bash
cd frontend
npm ci
npm run lint
npm run build
npm run dev
```
