#!/usr/bin/env bash
# setup.sh — Run once before starting the RAG PoC.
# Verifies Ollama, pulls required models, installs Python dependencies.

set -e

echo "=== RAG PoC Setup ==="

# 1. Check Ollama is running
echo "[1/4] Checking Ollama..."
if ! curl -s http://localhost:11434/api/tags > /dev/null; then
  echo "ERROR: Ollama is not running. Start it with: ollama serve"
  exit 1
fi
echo "  Ollama OK"

# 2. Pull embedding model if not present
EMBED_MODEL=$(grep -E '^EMBED_MODEL=' .env | cut -d= -f2-)
echo "[2/4] Checking embedding model ($EMBED_MODEL)..."
if ! ollama list | awk '{print $1}' | grep -qx "$EMBED_MODEL"; then
  echo "  Pulling $EMBED_MODEL (~5GB, this may take several minutes)..."
  ollama pull "$EMBED_MODEL"
else
  echo "  $EMBED_MODEL already present"
fi

# 3. Pull chat model if not present
CHAT_MODEL=$(grep -E '^CHAT_MODEL=' .env | cut -d= -f2-)
echo "[3/4] Checking chat model ($CHAT_MODEL)..."
if ! ollama list | awk '{print $1}' | grep -qx "$CHAT_MODEL"; then
  echo "  Pulling $CHAT_MODEL..."
  ollama pull "$CHAT_MODEL"
else
  echo "  $CHAT_MODEL already present"
fi

# 4. Install Python dependencies (root + cli + visualizer)
echo "[4/4] Installing Python dependencies..."
if ! command -v uv > /dev/null; then
  echo "ERROR: uv is not installed. Install it from https://docs.astral.sh/uv/"
  exit 1
fi

uv sync
( cd cli && uv sync )
( cd visualizer && uv sync )

echo ""
echo "=== Setup complete! ==="
echo "Next steps:"
echo "  1. uv run python ingest.py --docs ./docs --version v1   # Ingest docs"
echo "  2. uv run python ingest.py --list                       # Verify"
echo "  3. uv run python smoke_test.py                          # End-to-end test"
echo "  4. cd cli && uv run python main.py ../mcp_rag_server.py # Start chat"
