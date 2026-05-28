#!/usr/bin/env bash
set -e

if [ "${USE_OLLAMA:-true}" = "true" ]; then
  echo "Starting Ollama service on 0.0.0.0:11434..."
  ollama serve --listen 0.0.0.0:11434 &
fi

exec uvicorn server:app --host 0.0.0.0 --port 7860
