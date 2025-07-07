запустить весь проект фронт + бэк (команду запускать в корне проекта)
docker-compose up --build

запустить бэк (команду запускать в корне проекта)
uvicorn app.main:app --reload

запустить фронт (команды запускать в папке frontend)
yarn
yarn dev

сбилдить проект
docker build -t myproject .
docker run -d -p 80:8000 myproject
