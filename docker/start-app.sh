#!/bin/bash

# Start the Flask trading application
cd /home/trader/app

# Wait for database to be ready (if using external DB)
echo "Waiting for database connection..."
sleep 10

# Set up environment
export PYTHONPATH="/home/trader/app/src"
export PATH="/home/trader/.local/bin:$PATH"

# Create necessary directories
mkdir -p logs reports results data/stock_data data/fx_data

# Database migrations are an explicit deployment step, not run here (docs/development/DATABASE_MIGRATIONS.md):
#   docker compose run --rm app alembic upgrade head

# Start the Flask application
echo "Starting Flask application..."
exec python -m src.interfaces.flask.flask