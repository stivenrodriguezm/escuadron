#!/usr/bin/env bash
# Arranque unificado: backend (FastAPI + motor de agentes) sirviendo el frontend compilado.
#   ./start.sh          → instala lo necesario, compila la UI y deja el sistema en segundo plano
#   ./start.sh stop     → detiene el servidor
#   ./start.sh status   → estado del proceso
#   ./start.sh dev      → backend con recarga + Vite dev server (desarrollo)
#   ./start.sh test     → ejecuta los tests matemáticos
set -euo pipefail
cd "$(dirname "$0")"

PORT="${API_PORT:-8000}"
HOST="${HOST:-127.0.0.1}"  # solo esta máquina: la API no tiene autenticación
PID_FILE="logs/server.pid"
LOG_FILE="logs/server.log"
mkdir -p logs data

ensure_backend() {
  if [ ! -x .venv/bin/python ]; then
    python3 -m venv .venv
  fi
  if [ ! -f .venv/.deps-installed ] || [ requirements.txt -nt .venv/.deps-installed ]; then
    .venv/bin/pip install -q -r requirements.txt
    touch .venv/.deps-installed
  fi
  [ -f .env ] || cp .env.example .env
}

ensure_frontend() {
  [ -d frontend/node_modules ] || (cd frontend && npm install --no-audit --no-fund)
  if [ ! -f frontend/dist/index.html ] || [ -n "$(find frontend/src -newer frontend/dist/index.html -print -quit)" ]; then
    (cd frontend && npm run build)
  fi
}

is_running() { [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; }

case "${1:-start}" in
  start)
    if is_running; then echo "Ya está en ejecución (PID $(cat "$PID_FILE")) → http://localhost:$PORT"; exit 0; fi
    ensure_backend
    ensure_frontend
    nohup .venv/bin/uvicorn backend.api.main:app --host "$HOST" --port "$PORT" >>"$LOG_FILE" 2>&1 &
    echo $! >"$PID_FILE"
    echo "Sistema operando en segundo plano (PID $!) → http://localhost:$PORT  ·  logs: $LOG_FILE"
    ;;
  stop)
    if is_running; then kill "$(cat "$PID_FILE")" && rm -f "$PID_FILE" && echo "Detenido."; else echo "No está en ejecución."; fi
    ;;
  status)
    if is_running; then echo "En ejecución (PID $(cat "$PID_FILE")) → http://localhost:$PORT"; else echo "Detenido."; fi
    ;;
  dev)
    ensure_backend
    [ -d frontend/node_modules ] || (cd frontend && npm install --no-audit --no-fund)
    trap 'kill 0' EXIT
    .venv/bin/uvicorn backend.api.main:app --reload --reload-dir backend --port "$PORT" &
    (cd frontend && npm run dev)
    ;;
  test)
    ensure_backend
    .venv/bin/python -m pytest -q
    ;;
  *)
    echo "Uso: $0 [start|stop|status|dev|test]"; exit 1
    ;;
esac
