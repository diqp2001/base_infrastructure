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

# Run database migrations if needed
# python -m alembic upgrade head  # Uncomment if using Alembic

# Start the Flask application
echo "Starting Flask application..."
exec python -m src.interfaces.flask.flask