#!/bin/bash

echo "Starting Redis server..."
redis-server --daemonize yes --port 6379 --bind 127.0.0.1 --loglevel warning

sleep 2

redis-cli ping > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "Redis started successfully"
else
    echo "Warning: Redis may not have started properly"
fi

echo "Starting Discord bot..."
python main.py
