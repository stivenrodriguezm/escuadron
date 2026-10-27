#!/usr/bin/env bash
# Arranque unificado: backend (FastAPI + motor de agentes) sirviendo el frontend compilado.
#   ./start.sh                    → instala lo necesario, compila la UI y deja el sistema en segundo plano
#   ./start.sh stop               → detiene el servidor
#   ./start.sh status             → estado del proceso
#   ./start.sh install-service    → macOS: servidor permanente (arranca al iniciar sesión, se reinicia
#                                   solo si falla e impide que el Mac se duerma con el cargador puesto)
#   ./start.sh uninstall-service  → quita el servicio permanente
#   ./start.sh dev                → backend con recarga + Vite dev server (desarrollo)
#   ./start.sh test               → ejecuta los tests matemáticos
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(pwd -P)"  # ruta real: el servicio no puede usar el acceso directo del Escritorio

PORT="${API_PORT:-8000}"
HOST="${HOST:-127.0.0.1}"  # solo esta máquina: la API no tiene autenticación
PID_FILE="logs/server.pid"
LOG_FILE="logs/server.log"
LABEL="com.escuadron.motor"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
# launchd no puede abrir rutas del Escritorio (protección de privacidad de macOS):
# el lanzador y el log del servicio viven fuera de él.
SERVICE_DIR="$HOME/Library/Application Support/Escuadron"
SERVICE_LOG="$HOME/Library/Logs/Escuadron/server.log"
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

# ---------- servicio launchd (macOS) ----------
service_installed() { [ "$(uname)" = "Darwin" ] && [ -f "$PLIST" ]; }
service_target() { echo "gui/$(id -u)/$LABEL"; }
service_pid() { launchctl print "$(service_target)" 2>/dev/null | awk '/^\tpid = / {print $3; exit}'; }

write_plist() {
  mkdir -p "$(dirname "$PLIST")" "$SERVICE_DIR" "$(dirname "$SERVICE_LOG")"
  cat >"$SERVICE_DIR/run.sh" <<EOF
#!/bin/bash
# Lanzador del servicio (generado por start.sh install-service).
cd "$ROOT" || exit 78
# caffeinate: impide el reposo por inactividad (-i) y, con cargador, el del sistema (-s)
exec /usr/bin/caffeinate -i -s "$ROOT/.venv/bin/uvicorn" backend.api.main:app \\
  --host "$HOST" --port "$PORT" --no-access-log
EOF
  chmod +x "$SERVICE_DIR/run.sh"
  cat >"$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array><string>/bin/bash</string><string>$SERVICE_DIR/run.sh</string></array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>15</integer>
  <key>ProcessType</key><string>Interactive</string>
  <key>StandardOutPath</key><string>$SERVICE_LOG</string>
  <key>StandardErrorPath</key><string>$SERVICE_LOG</string>
  <key>EnvironmentVariables</key>
  <dict><key>PATH</key><string>/usr/bin:/bin:/usr/sbin:/sbin</string></dict>
</dict>
</plist>
EOF
}

service_start() {
  launchctl bootstrap "gui/$(id -u)" "$PLIST" 2>/dev/null || true
  launchctl kickstart "$(service_target)" 2>/dev/null || true
}

case "${1:-start}" in
  start)
    if service_installed; then
      ensure_frontend
      service_start
      echo "Servicio permanente activo (PID $(service_pid)) → http://localhost:$PORT  ·  logs: $SERVICE_LOG"
      exit 0
    fi
    if is_running; then echo "Ya está en ejecución (PID $(cat "$PID_FILE")) → http://localhost:$PORT"; exit 0; fi
    ensure_backend
    ensure_frontend
    nohup .venv/bin/uvicorn backend.api.main:app --host "$HOST" --port "$PORT" >>"$LOG_FILE" 2>&1 &
    echo $! >"$PID_FILE"
    echo "Sistema operando en segundo plano (PID $!) → http://localhost:$PORT  ·  logs: $LOG_FILE"
    ;;
  stop)
    if service_installed; then
      launchctl bootout "$(service_target)" 2>/dev/null && echo "Servicio detenido (volverá a arrancar al iniciar sesión; para quitarlo: ./start.sh uninstall-service)." \
        || echo "El servicio no estaba en ejecución."
    elif is_running; then kill "$(cat "$PID_FILE")" && rm -f "$PID_FILE" && echo "Detenido."
    else echo "No está en ejecución."; fi
    ;;
  status)
    if service_installed; then
      pid=$(service_pid)
      if [ -n "$pid" ]; then echo "Servicio permanente en ejecución (PID $pid) → http://localhost:$PORT"
      else echo "Servicio permanente instalado pero detenido (./start.sh start)."; fi
    elif is_running; then echo "En ejecución (PID $(cat "$PID_FILE")) → http://localhost:$PORT"
    else echo "Detenido."; fi
    ;;
  install-service)
    [ "$(uname)" = "Darwin" ] || { echo "install-service es para macOS; en Linux usa docker-compose.prod.yml."; exit 1; }
    ensure_backend
    ensure_frontend
    if is_running; then kill "$(cat "$PID_FILE")" && rm -f "$PID_FILE"; sleep 2; fi  # evita dos motores en el puerto
    launchctl bootout "$(service_target)" 2>/dev/null || true
    write_plist
    service_start
    sleep 3
    echo "Servicio permanente instalado (PID $(service_pid)). Arrancará solo cada vez que inicies sesión."
    echo "Logs: $SERVICE_LOG"
    ;;
  uninstall-service)
    launchctl bootout "$(service_target)" 2>/dev/null || true
    rm -f "$PLIST" "$SERVICE_DIR/run.sh"
    echo "Servicio permanente eliminado."
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
    echo "Uso: $0 [start|stop|status|install-service|uninstall-service|dev|test]"; exit 1
    ;;
esac
