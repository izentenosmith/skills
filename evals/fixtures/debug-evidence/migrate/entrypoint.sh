#!/bin/sh
set -eu
echo "applying migrations"
exec python /app/migrate.py
