# Сборка сайта
#
# Готовый образ вместо ubuntu:22.04 + wget: раньше каждая сборка тянула с
# GitHub 40+ МБ архива Hugo, без сверки контрольной суммы, и ломалась, если
# GitHub недоступен. Версия теперь зафиксирована тегом образа.
#
# base — минимальный вариант hugomods: только Hugo, без Node, Go и Git,
# которые проекту не нужны (модули Hugo не используются, enableGitInfo не
# задан, тема PaperMod лежит каталогом в themes/).
#
# Редакция именно extended — у hugomods это теги БЕЗ префикса std. Прежний
# Dockerfile качал hugo_extended, и менять редакцию заодно с переездом на
# готовый образ незачем: PaperMod проверяет hugo.IsExtended и добавляет webp
# в список обрабатываемых форматов обложек.
FROM hugomods/hugo:base-0.146.0 AS builder

WORKDIR /src

COPY . .

# Build static site
RUN hugo --minify

# Production stage
FROM nginx:alpine

# Copy built site from builder
COPY --from=builder /src/public /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80


CMD ["nginx", "-g", "daemon off;"]
