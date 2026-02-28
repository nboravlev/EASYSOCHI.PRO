FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create non-root user for security and set proper permissions
RUN useradd -m -u 1000 easysochipro && \
    chown -R easysochipro:easysochipro /app

# Switch to non-root user
USER easysochipro

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
