# EasySochi Main Project 🚀

Центральный узел экосистемы EasySochi. Проект объединяет фронтенд на Hugo, бэкенд на Python (FastAPI), базу данных PostgreSQL, реверс-прокси nginx и мониторинг статистики через GoAccess.

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
cp .env.example .env
```

### 3. Создание .htpasswd для stats.easysochi.pro
```bash
htpasswd -c .htpasswd <username>
```

### 4. Запуск
```bash
docker compose up -d --build
```

## 📂 Структура проекта

- `/easysochi-site` — фронтенд Hugo
- `/easysochi-backend` — бэкенд FastAPI
- `/nginx` — конфиг внутреннего реверс-прокси
- `/docker-compose.yml` — описание сервисов

## 🔐 Безопасность

- Все секреты хранятся в `.env` и не попадают в репозиторий
- Сервисы не имеют прямых портов наружу — только через nginx
- Вебхуки платёжных систем защищены через geo-фильтрацию по IP
- stats.easysochi.pro защищён basic auth

## 📄 Лицензия

Copyright © 2026 EasySochi. Все права защищены.