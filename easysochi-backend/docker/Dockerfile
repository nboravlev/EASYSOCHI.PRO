FROM python:3.11-slim

# Без этого stdout буферизуется при выводе в пайп, и логи миграций теряются,
# если контейнер падает на alembic upgrade.
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create non-root user for security and set proper permissions
RUN useradd -m -u 1000 easysochipro && \
    chmod +x /app/entrypoint.sh && \
    chown -R easysochipro:easysochipro /app

# Switch to non-root user
USER easysochipro

# entrypoint.sh применяет миграции и затем запускает uvicorn
CMD ["/app/entrypoint.sh"]
