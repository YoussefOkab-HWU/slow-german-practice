#!/bin/bash
cd "$(dirname "$0")"
# Kill any existing instance on port 8080
pkill -f "python3 serve.py" 2>/dev/null
sleep 0.3
# Start server in background, log to /tmp
python3 serve.py > /tmp/slow_german.log 2>&1 &
# Wait for Flask to bind
sleep 1.2
xdg-open http://localhost:8080
