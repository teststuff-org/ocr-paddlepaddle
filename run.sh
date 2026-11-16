#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

# Écoute par défaut sur 127.0.0.1 seulement : l'API n'est joignable que depuis cette machine.
# Pour exposer l'API sur le réseau local : HOST=0.0.0.0 ./run.sh
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

# Rechargement à chaud désactivé par défaut, pour la même raison que dans run.ps1 : un reloader
# figé laisse un worker orphelin qui garde le port et sert l'ancien code. Pour développer :
# ./run.sh start --reload   (ou RELOAD=true ./run.sh)
RELOAD="${RELOAD:-false}"
if [ "${2:-}" = "--reload" ]; then RELOAD="true"; fi
RELOAD_ARGS=()
if [ "$RELOAD" = "true" ]; then RELOAD_ARGS=(--reload); fi

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

api_root_pid() {
  # Remonte les parents tant qu'ils appartiennent à cette API : tuer le seul processus qui tient
  # le port laisse le lanceur (`uv run uvicorn`, reloader) en vie, et il peut relancer un worker
  # qui resservira l'ancien code.
  local pid="$1" ppid cmd
  for _ in $(seq 1 10); do
    ppid="$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ')"
    [ -n "$ppid" ] || break
    cmd="$(ps -o args= -p "$ppid" 2>/dev/null)"
    case "$cmd" in
      *uvicorn*|*app.main*) pid="$ppid" ;;
      *) break ;;
    esac
  done
  echo "$pid"
}

descendants() {
  # Descendants d'un PID, du plus profond au plus haut : un parent survivant relancerait son fils.
  local parent="$1" child
  for child in $(pgrep -P "$parent" 2>/dev/null); do
    descendants "$child"
    echo "$child"
  done
}

stop_server() {
  if ! port_open; then
    echo "Aucun serveur n'ecoute sur le port $PORT."
    return 0
  fi

  local pid root
  pid="$(listener_pid)"
  if [ -z "$pid" ]; then
    echo "Le port $PORT repond mais son PID est introuvable (lsof/ss/fuser absents)." >&2
    echo "Arretez-le manuellement, ou installez lsof." >&2
    return 1
  fi

  root="$(api_root_pid "$pid")"
  echo "Arret du serveur (PID $pid, racine $root)..."
  # SIGTERM d'abord : uvicorn termine les requetes en cours. Ensuite, descendants et racine
  # sont arretes du plus profond au plus haut : un parent survivant relancerait son fils, qui
  # garderait le port et servirait l'ancien code.
  kill -TERM "$root" 2>/dev/null || true

  for _ in $(seq 1 40); do
    sleep 0.25
    if ! port_open; then
      echo "Serveur arrete, port $PORT libre."
      return 0
    fi
  done

  echo "Toujours actif apres 10 s : arret force." >&2
  for child in $(descendants "$root"); do kill -KILL "$child" 2>/dev/null || true; done
  kill -KILL "$root" 2>/dev/null || true
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
  if [ "$RELOAD" = "true" ]; then
    echo "Rechargement : actif"
  else
    echo "Rechargement : desactive (relancez ./run.sh apres une modification du code)"
  fi

  if command -v uv >/dev/null 2>&1; then
    [ -d .venv ] || uv venv
    uv pip install -r requirements.txt
    uv run uvicorn app.main:app --host "$HOST" --port "$PORT" ${RELOAD_ARGS[@]+"${RELOAD_ARGS[@]}"}
  else
    echo "uv introuvable, utilisation de venv + pip (installer uv : https://docs.astral.sh/uv/)"
    [ -d .venv ] || python3 -m venv .venv
    . .venv/bin/activate
    pip install -r requirements.txt
    uvicorn app.main:app --host "$HOST" --port "$PORT" ${RELOAD_ARGS[@]+"${RELOAD_ARGS[@]}"}
  fi
}

case "${1:-start}" in
  start) start_server ;;
  stop) stop_server ;;
  *)
    echo "Usage : ./run.sh [start|stop] [--reload]" >&2
    echo "  start     demarre l'API (defaut)" >&2
    echo "  stop      arrete l'arbre de processus qui ecoute sur le port" >&2
    echo "  --reload  rechargement a chaud (deconseille : workers figes)" >&2
    echo "Variables : PORT (defaut 8000), HOST (defaut 127.0.0.1), RELOAD (true|false)" >&2
    exit 2
    ;;
esac
