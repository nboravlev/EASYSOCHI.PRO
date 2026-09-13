# EasySochi Main Project 🚀

Центральный узел экосистемы EasySochi. Проект объединяет фронтенд на Hugo, бэкенд на Python (FastAPI), базу данных PostgreSQL, реверс-прокси nginx и мониторинг статистики через GoAccess.

Порядок работы над проектом — ветки, содержание PR, проверка на сервере перед мержем — описан в [CONTRIBUTING.md](CONTRIBUTING.md).

## 🛠 Технологический стек
- **Frontend:** Hugo (Static Site Generator)
- **Backend:** Python (FastAPI)
- **Database:** PostgreSQL 15
- **Proxy:** Nginx (внутренний реверс-прокси)
- **Analytics:** GoAccess (real-time статистика)
- **Infrastructure:** Docker Compose

## 🏗 Архитектура
Проект работает за общим верхним прокси (upper-proxy), который терминирует SSL и проксирует трафик на порт 21500. Внутренний nginx принимает трафик и маршрутизирует по сервисам.
```
Интернет → upper-proxy (SSL) → nginx :21500 → easysochi-site :80
                                              → contact_api :8000
                                              → goaccess_pro :7890
```

Все сервисы общаются через внутреннюю сеть `easysochipro_net`. Наружу торчит только nginx.

## 📦 Развертывание

### 1. Подготовка папок на HDD
```bash
sudo mkdir -p /data/easysochi_pro/{postgres_data,media,logs,stats}
sudo chown -R 999:999 /data/easysochi_pro/postgres_data
sudo chown -R 1000:1000 /data/easysochi_pro/media
sudo chown -R 101:101 /data/easysochi_pro/logs
sudo chown -R 101:101 /data/easysochi_pro/stats
```

### 2. Подготовка переменных
```bash
cp deploy/.env.example deploy/.env
```

### 3. Создание .htpasswd для stats.easysochi.pro

> ⚠️ **Обязательный шаг — выполнить до `docker compose up`.**
> Файл `.htpasswd` не хранится в репозитории (он в `.gitignore`), поэтому после
> `git clone` его на сервере нет. В `deploy/docker-compose.yml` он монтируется как
> `./.htpasswd:/etc/nginx/.htpasswd:ro`, то есть ожидается в каталоге `deploy/`
> рядом с compose-файлом. Если файла не существует, Docker создаст на его месте
> **директорию**, и контейнер nginx упадёт при старте.

```bash
htpasswd -c deploy/.htpasswd <username>
```

### 4. Запуск
```bash
./deploy/build.sh
```

Скрипт проверяет предусловия, собирает образы, поднимает стек, дожидается
статуса `healthy` у всех сервисов с healthcheck и прогоняет проверки API.
При неудаче сам печатает диагностику — состояние контейнеров и хвост логов
тех, что не поднялись. Справка: `./deploy/build.sh --help`.

Образы помечаются тегом — коротким хешем текущего коммита — и дополнительно
как `:latest`. Откат на предыдущую сборку без пересборки:

```bash
cd deploy && TAG=<хеш> docker compose up -d
```

Доступные теги: `docker images easysochi/contact-api`.

### 5. Ротация логов nginx
Логи пишутся на HDD и читаются GoAccess, поэтому ротация настраивается на хосте,
а не внутри контейнера. Конфиг лежит в репозитории:

```bash
sudo cp deploy/logrotate/easysochi_pro /etc/logrotate.d/easysochi_pro
sudo logrotate -d /etc/logrotate.d/easysochi_pro
```

Вторая команда прогоняет logrotate вхолостую и показывает, что бы он сделал,
ничего не меняя. GoAccess запущен с `--persist/--restore`, поэтому обрезание
лога не стирает накопленную статистику.

## 📂 Структура проекта

Каждый сервис держит свой Dockerfile в собственном каталоге `docker/`, а всё,
что относится к развёртыванию, собрано в `deploy/`.

```
easysochi-site/          фронтенд Hugo
  docker/Dockerfile
  .dockerignore
easysochi-backend/       бэкенд FastAPI
  docker/Dockerfile
  .dockerignore
nginx/                   внутренний реверс-прокси
  docker/Dockerfile
  nginx.conf, conf.d/
deploy/                  всё о развёртывании
  docker-compose.yml     описание сервисов
  build.sh               сборка, запуск и проверка одной командой
  .env.example           шаблон переменных окружения
  .env                   рабочие переменные (в репозиторий не попадает)
  .htpasswd              basic auth для stats (в репозиторий не попадает)
  logrotate/             конфиг ротации логов для хоста
CONTRIBUTING.md          порядок разработки и проверки изменений
progress.md              журнал работ и бэклог
```

Команды `docker compose` выполняются из каталога `deploy/` — там лежит
compose-файл, и оттуда же берутся `.env` и `.htpasswd`.

## 🔐 Безопасность

- Все секреты хранятся в `.env` и не попадают в репозиторий
- Сервисы не имеют прямых портов наружу — только через nginx
- Вебхуки платёжных систем защищены через geo-фильтрацию по IP
- stats.easysochi.pro защищён basic auth

## 📄 Лицензия

Copyright © 2026 EasySochi. Все права защищены.
