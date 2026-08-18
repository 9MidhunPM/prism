#!/bin/sh
set -eu

# Schema migrations must run before the API imports routes that query new tables.
# Dokploy's environment can be temporarily set to development during provisioning.
alembic upgrade head

exec "$@"
