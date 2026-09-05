#!/bin/sh
set -e

echo "Starting Ollama server..."
ollama serve &
SERVE_PID=$!

echo "Waiting for Ollama server to be ready..."
until ollama list >/dev/null 2>&1; do
  sleep 1
done

if [ -n "$MODEL_NAME" ]; then
  echo "Pulling model: $MODEL_NAME"
  ollama pull "$MODEL_NAME"
  echo "Model $MODEL_NAME ready."
fi

wait "$SERVE_PID"
