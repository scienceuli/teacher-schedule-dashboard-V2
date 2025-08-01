#!/bin/bash
# Wait for PostgreSQL to be ready (optional, but useful)
echo "Waiting for PostgreSQL..."
while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
  sleep 0.1
done
echo "PostgreSQL is up."

# Run migrations
echo "Running migrations..."
export FLASK_APP=app.py
flask db upgrade

# Start Gunicorn
exec gunicorn --bind 0.0.0.0:5001 app:app
