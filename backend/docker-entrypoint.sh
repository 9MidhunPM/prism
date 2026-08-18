#!/bin/sh
set -eu

if [ "${APP_ENV:-development}" = "production" ]; then
  alembic upgrade head
fi

exec "$@"
