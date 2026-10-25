#!/bin/sh
set -e

if [ "$1" = "daphne" ] || [ "$1" = "python" ]; then
  echo "[Entrypoint] Running database migrations..."
  python manage.py migrate --noinput
fi

echo "[Entrypoint] Starting service: $@"
exec "$@"
