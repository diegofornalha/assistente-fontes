#!/bin/bash
# Watchdog para manter o backend sempre ativo

PORT=8182
VENV="/home/dados/assistente-dados/.venv/bin/python"
DIR="/home/dados/assistente-dados/backend-dados"
LOG="/home/dados/assistente-dados/server.log"

while true; do
    if ! curl -s -o /dev/null -w "" http://localhost:$PORT/docs 2>/dev/null; then
        echo "[$(date)] Backend caiu. Reiniciando..." >> /home/dados/assistente-dados/watchdog.log
        cd "$DIR"
        nohup $VENV -m uvicorn main:app --host 0.0.0.0 --port $PORT >> "$LOG" 2>&1 &
        sleep 5
    fi
    sleep 30
done
