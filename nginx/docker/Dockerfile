FROM nginx:alpine

# Устанавливаем envsubst (уже есть в nginx:alpine, но на всякий случай)
RUN apk add --no-cache gettext

# Копируем шаблон и вспомогательные конфиги
COPY nginx.conf /etc/nginx/nginx.conf
COPY conf.d/easysochi.conf.template /etc/nginx/templates/easysochi.conf.template
COPY conf.d/real_ip.conf /etc/nginx/conf.d/real_ip.conf
COPY conf.d/payments_ids.geo /etc/nginx/conf.d/payments_ids.geo

EXPOSE 21500