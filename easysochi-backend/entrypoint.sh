#!/bin/sh
# Точка входа contact_api.
#
# Схема БД создаётся только миграциями Alembic. Раньше их приходилось
# применять руками, а startup-хук в main.py вызывал create_all у Base из
# db_async.py — у него пустая metadata, потому что все модели наследуются от
# Base из db.py. То есть на чистом сервере таблиц не появлялось вообще.
set -e

echo "[entrypoint] alembic upgrade head"
alembic upgrade head

echo "[entrypoint] starting uvicorn"
exec uvicorn main:app --host 0.0.0.0 --port 8000
