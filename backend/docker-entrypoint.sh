#!/bin/sh
set -eu

if [ "${APP_ENV:-development}" = "production" ]; then
  : "${DATABASE_URL:?DATABASE_URL must be set in production}"
  alembic upgrade head
fi

exec "$@"
