#!/bin/sh
set -e

# Wait for the database to be ready (optional, but good practice)
# Example for PostgreSQL:
# until pg_isready -h ${DB_HOST:-db} -p ${DB_PORT:-5432} -U ${DB_USER:-user}; do
#   echo "Waiting for database..."
#   sleep 2
# done
# echo "Database is ready."

echo "Running database migrations..."
# Replace with your actual migration command
# If using Alembic:
alembic upgrade head
# If using Yoyo Migrations (assuming DATABASE_URL is set):
# yoyo apply --database "$DATABASE_URL" ./migrations

echo "Migrations complete."

# Execute the command passed as arguments to this script (the Dockerfile's CMD)
exec "$@"