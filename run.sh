#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

# Écoute par défaut sur 127.0.0.1 seulement : l'API n'est joignable que depuis cette machine.
# Pour exposer l'API sur le réseau local : HOST=0.0.0.0 ./run.sh
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

port_open() {
  (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null
}

listener_pid() {
  if command -v lsof >/dev/null 2>&1; then
    lsof -ti "tcp:$PORT" -sTCP:LISTEN 2>/dev/null | head -1
  elif command -v ss >/dev/null 2>&1; then
    ss -ltnp "sport = :$PORT" 2>/dev/null | grep -o 'pid=[0-9]*' | head -1 | cut -d= -f2
  elif command -v fuser >/dev/null 2>&1; then
    fuser -n tcp "$PORT" 2>/dev/null | tr -s ' ' '\n' | head -1
  fi
}

stop_server() {
  if ! port_open; then
    echo "Aucun serveur n'ecoute sur le port $PORT."
    return 0
  fi

  local pid
  pid="$(listener_pid)"
  if [ -z "$pid" ]; then
    echo "Le port $PORT repond mais son PID est introuvable (lsof/ss/fuser absents)." >&2
    echo "Arretez-le manuellement, ou installez lsof." >&2
    return 1
  fi

  echo "Arret du serveur (PID $pid)..."
  # Enfants d'abord : un worker orphelin garderait le port et servirait l'ancien code.
  # SIGTERM est gere par uvicorn (arret propre, requetes en cours terminees).
  pkill -TERM -P "$pid" 2>/dev/null || true
  kill -TERM "$pid" 2>/dev/null || true

  for _ in $(seq 1 40); do
    sleep 0.25
    if ! port_open; then
      echo "Serveur arrete, port $PORT libre."
      return 0
    fi
  done

  echo "Toujours actif apres 10 s : arret force." >&2
  pkill -KILL -P "$pid" 2>/dev/null || true
  kill -KILL "$pid" 2>/dev/null || true
  sleep 0.5
  if port_open; then
    echo "Le port $PORT repond encore." >&2
    return 1
  fi
  echo "Serveur arrete, port $PORT libre."
  return 0
}

start_server() {
  if port_open; then
    echo "Port $PORT deja occupe. Arretez-le avec : ./run.sh stop" >&2
    exit 1
  fi

  echo "API          : http://localhost:$PORT"
  echo "Swagger (UI) : http://localhost:$PORT/docs"
  echo "ReDoc        : http://localhost:$PORT/redoc"
  echo "Ecoute sur   : $HOST:$PORT"

  if command -v uv >/dev/null 2>&1; then
    [ -d .venv ] || uv venv
    uv pip install -r requirements.txt
    uv run uvicorn app.main:app --host "$HOST" --port "$PORT" --reload
  else
    echo "uv introuvable, utilisation de venv + pip (installer uv : https://docs.astral.sh/uv/)"
    [ -d .venv ] || python3 -m venv .venv
    . .venv/bin/activate
    pip install -r requirements.txt
    uvicorn app.main:app --host "$HOST" --port "$PORT" --reload
  fi
}

case "${1:-start}" in
  start) start_server ;;
  stop) stop_server ;;
  *)
    echo "Usage : ./run.sh [start|stop]" >&2
    echo "  start  demarre l'API (defaut)"
    echo "  stop   arrete le processus qui ecoute sur le port"
    echo "Variables : PORT (defaut 8000), HOST (defaut 127.0.0.1)"
    exit 2
    ;;
esac
