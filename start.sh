#!/usr/bin/env bash
set -e

export PATH="$HOME/.local/bin:$PATH"

if [ "${USE_OLLAMA:-true}" = "true" ]; then
  echo "Starting Ollama service on 0.0.0.0:11434..."
  ollama serve --listen 0.0.0.0:11434 &
  echo "Waiting briefly for Ollama to start..."
  sleep 5
  echo "Pulling llama3.2 model if needed..."
  ollama pull llama3.2 || true
fi

exec uvicorn server:app --host 0.0.0.0 --port 7860
