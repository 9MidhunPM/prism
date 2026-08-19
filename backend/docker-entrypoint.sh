#!/bin/sh
set -eu

# Schema migrations run once under a PostgreSQL advisory lock before the API starts.
python -m app.migrate

exec "$@"
