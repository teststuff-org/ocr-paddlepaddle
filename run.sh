#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

HOST=0.0.0.0
PORT=8000

echo "API          : http://localhost:$PORT"
echo "Swagger (UI) : http://localhost:$PORT/docs"
echo "ReDoc        : http://localhost:$PORT/redoc"

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
