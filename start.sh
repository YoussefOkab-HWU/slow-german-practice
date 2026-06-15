#!/bin/bash
cd "$(dirname "$0")"

# Install flask if missing
python3 -c "import flask" 2>/dev/null || pip install flask --break-system-packages 2>/dev/null || pip3 install flask --break-system-packages

# Kill any existing instance on port 8080
pkill -f "python3 serve.py" 2>/dev/null
sleep 0.5

# Start server in background
python3 serve.py > /tmp/slow_german.log 2>&1 &
sleep 1.2

xdg-open http://localhost:8080 2>/dev/null || open http://localhost:8080 2>/dev/null || echo "Open http://localhost:8080 in your browser"
