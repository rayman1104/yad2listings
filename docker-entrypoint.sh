#!/bin/bash
set -e

# Function to check if PostgreSQL is ready
wait_for_postgres() {
    echo "Waiting for PostgreSQL to be ready..."
    while ! python -c "import psycopg2; psycopg2.connect(\"${DATABASE_URL}\")" 2>/dev/null; do
        echo "PostgreSQL is unavailable - sleeping"
        sleep 1
    done
    echo "PostgreSQL is up and running!"
}

# Wait for PostgreSQL
wait_for_postgres

# Run migrations
echo "Running database migrations..."
python database/migrations.py

# Start the bot
echo "Starting Telegram bot..."
exec python telegram_bot.py
