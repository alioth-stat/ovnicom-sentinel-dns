#!/usr/bin/env bash
# Sets up (if needed) and runs the backend + frontend dev servers together.
set -euo pipefail
cd "$(dirname "$0")"

# Check for the actual binary, not just the directory -- a venv left behind
# by a prior failed install would otherwise pass a bare `-d .venv` check and
# get silently skipped forever, with no fastapi/uvicorn ever installed into it.
if [ ! -x .venv/bin/uvicorn ]; then
    echo "Creando entorno virtual e instalando dependencias de Python..."
    [ -d .venv ] || python3 -m venv .venv
    .venv/bin/pip install -q -r requirements.txt
fi

if [ ! -d frontend/node_modules ]; then
    echo "Instalando dependencias del frontend..."
    (cd frontend && npm install)
fi

# Fail fast if another instance already holds these ports.
for port in 8000 5173; do
    if fuser "$port"/tcp >/dev/null 2>&1; then
        echo "El puerto $port ya está en uso -- ¿hay otra instancia corriendo? Detenla primero." >&2
        exit 1
    fi
done

cleanup() {
    echo "Deteniendo servidores..."
    fuser -k 8000/tcp 5173/tcp 2>/dev/null || true
}
trap cleanup EXIT INT TERM

.venv/bin/uvicorn api:app --port 8000 &
(cd frontend && npm run dev) &

echo ""
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo "(Ctrl+C para detener ambos)"

wait
