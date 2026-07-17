#!/bin/bash
# Start the Phase 1 API server
# Usage: ./run.sh

set -e

echo "Installing dependencies..."
pip install -r requirements.txt --break-system-packages -q

echo "Starting server..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
