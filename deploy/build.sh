#!/bin/sh
#
# Сборка, запуск и проверка стека EASYSOCHI.PRO.
#
# Живёт в deploy/ рядом с docker-compose.yml: вся конфигурация развёртывания
# собрана в одном каталоге, а Dockerfile каждого сервиса лежит в его
# собственном <сервис>/docker/.
#
# Что делает по шагам:
#   1. проверяет, что демон Docker доступен, а рядом лежат deploy/.env
#      и deploy/.htpasswd
#   2. вычисляет тег образов: короткий хеш текущего коммита, плюс суффикс
#      -dirty, если в рабочем дереве есть незакоммиченные правки
#   3. собирает образы с этим тегом и дополнительно метит их как :latest
#   4. поднимает стек
#   5. ждёт, пока сервисы с healthcheck отрапортуют healthy
#   6. прогоняет проверки API внутри контейнера contact_api
#
# При любой неудаче печатает диагностику: состояние контейнеров и хвост
# логов тех из них, что не поднялись.
#
set -e

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

CHECK_SCRIPT="$ROOT_DIR/easysochi-backend/app/test/check_payment_api.py"
API_CONTAINER=easysochi_contact_api

# Сервисы, у которых в docker-compose.yml объявлен healthcheck.
# У nginx его нет — для него проверяем только факт запуска.
HEALTHCHECKED="postgres_db_easysochi easysochi_site easysochi_contact_api"
HEALTH_TIMEOUT=180

SKIP_TESTS=0
NO_CACHE=0
TAG=""

usage() {
  SCRIPT_NAME=$(basename "$0")

  printf "Usage:\n"
  printf "  %s [--tag <тег>] [--skip-tests] [--no-cache]\n" "$SCRIPT_NAME"
  printf "  %s --help\n\n" "$SCRIPT_NAME"
  printf "Собирает образы, поднимает стек и прогоняет проверки API.\n\n"
  printf "Опции:\n"
  printf "  --tag <тег>    тег образов (по умолчанию — короткий хеш коммита)\n"
  printf "  --skip-tests   не прогонять проверки API после запуска\n"
  printf "  --no-cache     пересобрать образы без использования кеша\n"
  printf "  -h, --help     показать эту справку\n\n"
  printf "Откат на предыдущую сборку (образ должен остаться на диске):\n"
  printf "  cd deploy && TAG=<тег> docker compose up -d\n"
  printf "  docker images easysochi/contact-api   — посмотреть доступные теги\n"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    -h | --help)
      usage
      exit 0
      ;;
    --skip-tests)
      SKIP_TESTS=1
      shift
      ;;
    --no-cache)
      NO_CACHE=1
      shift
      ;;
    --tag)
      if [ -z "${2:-}" ]; then
        printf "Опция --tag требует значения.\n\n" >&2
        usage >&2
        exit 1
      fi
      TAG=$2
      shift 2
      ;;
    *)
      printf "Неизвестный аргумент: %s\n\n" "$1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

# ----------------------------------------------------------------- оформление

if [ -t 1 ]; then
  ESC=$(printf "\033")
  GREEN="${ESC}[32m"
  RED="${ESC}[31m"
  YELLOW="${ESC}[33m"
  BOLD="${ESC}[1m"
  RESET="${ESC}[0m"
else
  GREEN=""
  RED=""
  YELLOW=""
  BOLD=""
  RESET=""
fi

step() { printf "\n%s==> %s%s\n" "$BOLD" "$1" "$RESET"; }
ok() { printf "%s  ok%s    %s\n" "$GREEN" "$RESET" "$1"; }
warn() { printf "%s  !!%s    %s\n" "$YELLOW" "$RESET" "$1"; }
fail() { printf "%s  FAIL%s  %s\n" "$RED" "$RESET" "$1" >&2; }

# ----------------------------------------------------------------- диагностика

dump_diagnostics() {
  printf "\n%s=== Диагностика ===%s\n" "$RED" "$RESET"

  printf "\n--- docker compose ps ---\n"
  (cd "$SCRIPT_DIR" && docker compose ps) || true

  for CONTAINER in $HEALTHCHECKED easysochi_nginx; do
    STATUS=$(docker inspect -f "{{.State.Status}}" "$CONTAINER" 2>/dev/null || echo "отсутствует")
    HEALTH=$(docker inspect -f "{{if .State.Health}}{{.State.Health.Status}}{{else}}без healthcheck{{end}}" "$CONTAINER" 2>/dev/null || echo "-")

    # Логи показываем только у проблемных: у здоровых они лишний шум.
    NEEDS_LOGS=0
    [ "$STATUS" != "running" ] && NEEDS_LOGS=1
    [ "$HEALTH" = "unhealthy" ] && NEEDS_LOGS=1
    [ "$HEALTH" = "starting" ] && NEEDS_LOGS=1

    if [ "$NEEDS_LOGS" -eq 1 ]; then
      printf "\n--- %s (status=%s, health=%s), последние 50 строк ---\n" "$CONTAINER" "$STATUS" "$HEALTH"
      docker logs "$CONTAINER" --tail 50 2>&1 || true
    fi
  done

  printf "\nПолные логи: docker logs <контейнер> --tail 200\n"
}

on_exit() {
  RC=$?
  if [ "$RC" -ne 0 ]; then
    dump_diagnostics
  fi
  exit "$RC"
}

# ----------------------------------------------------------------- предпроверки

step "Предварительные проверки"

if ! docker info >/dev/null 2>&1; then
  fail "демон Docker недоступен, запустите Docker и повторите"
  exit 1
fi
ok "демон Docker доступен"

# compose не предупреждает об отсутствии .env, а жёстко падает с
# "env file not found", поэтому проверяем заранее и с понятным сообщением.
# Файл ищется рядом с compose-файлом, то есть в deploy/.
if [ ! -f "$SCRIPT_DIR/.env" ]; then
  fail "нет файла .env в $SCRIPT_DIR"
  if [ -f "$ROOT_DIR/.env" ]; then
    printf "  Похоже, он остался в корне проекта после переезда конфигурации в deploy/.\n" >&2
    printf "  Перенесите: mv %s/.env %s/.env\n" "$ROOT_DIR" "$SCRIPT_DIR" >&2
  else
    printf "  Создайте его из шаблона: cp deploy/.env.example deploy/.env\n" >&2
  fi
  exit 1
fi
ok ".env на месте"

if [ ! -f "$SCRIPT_DIR/.htpasswd" ]; then
  fail "нет файла .htpasswd в $SCRIPT_DIR"
  if [ -f "$ROOT_DIR/.htpasswd" ]; then
    printf "  Похоже, он остался в корне проекта после переезда конфигурации в deploy/.\n" >&2
    printf "  Перенесите: mv %s/.htpasswd %s/.htpasswd\n" "$ROOT_DIR" "$SCRIPT_DIR" >&2
  else
    printf "  Без него Docker создаст на месте bind-mount директорию и nginx не поднимется.\n" >&2
    printf "  Создайте его: htpasswd -c deploy/.htpasswd <имя_пользователя>\n" >&2
  fi
  exit 1
fi
ok ".htpasswd на месте"

# ----------------------------------------------------------------- тег образов

if [ -z "$TAG" ]; then
  if git -C "$ROOT_DIR" rev-parse --short HEAD >/dev/null 2>&1; then
    TAG=$(git -C "$ROOT_DIR" rev-parse --short HEAD)
    # Суффикс -dirty честно говорит, что образ не воспроизводится из коммита.
    if [ -n "$(git -C "$ROOT_DIR" status --porcelain)" ]; then
      TAG="${TAG}-dirty"
      warn "в рабочем дереве есть незакоммиченные правки, тег получит суффикс -dirty"
    fi
  else
    TAG=latest
    warn "каталог не под git, использую тег latest"
  fi
fi
export TAG
ok "тег образов: $TAG"

# ----------------------------------------------------------------- сборка

# Диагностику включаем только с этого момента: до сюда все отказы — это
# ошибка в аргументах или отсутствующий файл, и они печатают понятное
# сообщение сами. Вываливать на них состояние контейнеров незачем.
trap on_exit EXIT

step "Сборка образов"

if [ "$NO_CACHE" -eq 1 ]; then
  (cd "$SCRIPT_DIR" && docker compose build --no-cache)
else
  (cd "$SCRIPT_DIR" && docker compose build)
fi

# Дополнительно метим как :latest, чтобы обычный docker compose up -d без
# переменной TAG поднимал именно эту сборку.
if [ "$TAG" != "latest" ]; then
  for IMAGE in easysochi/site easysochi/contact-api easysochi/nginx; do
    docker tag "$IMAGE:$TAG" "$IMAGE:latest"
  done
  ok "образы дополнительно помечены как :latest"
fi

# ----------------------------------------------------------------- запуск

step "Запуск стека"
(cd "$SCRIPT_DIR" && docker compose up -d)

# ----------------------------------------------------------------- ожидание

wait_for_healthy() {
  CONTAINER=$1
  START=$(date +%s)

  while true; do
    STATUS=$(docker inspect -f "{{.State.Health.Status}}" "$CONTAINER" 2>/dev/null || echo "нет контейнера")
    NOW=$(date +%s)
    ELAPSED=$((NOW - START))

    if [ "$STATUS" = "healthy" ]; then
      ok "$CONTAINER — healthy (${ELAPSED}s)"
      return 0
    fi

    if [ "$STATUS" = "unhealthy" ]; then
      fail "$CONTAINER — unhealthy через ${ELAPSED}s"
      return 1
    fi

    if [ "$ELAPSED" -ge "$HEALTH_TIMEOUT" ]; then
      fail "$CONTAINER не стал healthy за ${HEALTH_TIMEOUT}s, последний статус: $STATUS"
      return 1
    fi

    sleep 2
  done
}

step "Ожидание готовности сервисов"
for CONTAINER in $HEALTHCHECKED; do
  wait_for_healthy "$CONTAINER"
done

NGINX_STATUS=$(docker inspect -f "{{.State.Status}}" easysochi_nginx 2>/dev/null || echo "отсутствует")
if [ "$NGINX_STATUS" = "running" ]; then
  ok "easysochi_nginx — running (healthcheck не объявлен)"
else
  fail "easysochi_nginx не запущен, статус: $NGINX_STATUS"
  exit 1
fi

# ----------------------------------------------------------------- проверки API

if [ "$SKIP_TESTS" -eq 1 ]; then
  step "Проверки API пропущены (--skip-tests)"
else
  step "Проверки API"
  # Скрипт подаётся на stdin, чтобы не зависеть от того, попал ли он в образ.
  docker exec -i "$API_CONTAINER" python3 - <"$CHECK_SCRIPT"
  ok "проверки API пройдены"
fi

# ----------------------------------------------------------------- итог

step "Готово"
printf "  тег сборки:      %s\n" "$TAG"
printf "  образы:          easysochi/site, easysochi/contact-api, easysochi/nginx\n"
printf "  откат на неё:    cd deploy && TAG=%s docker compose up -d\n" "$TAG"
printf "  доступные теги:  docker images easysochi/contact-api\n"
