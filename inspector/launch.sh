#!/usr/bin/env bash
# Launch the MCP Inspector against one of the project's MCP servers.
#
# Usage:
#   bash launch.sh rag    # inspect the RAG knowledge base server
#   bash launch.sh docs   # inspect the document MCP server
#
# Open: http://localhost:6274
set -e

TARGET=${1:-rag}
case "$TARGET" in
  rag|docs) ;;
  *)
    echo "Unknown target '$TARGET'. Use 'rag' or 'docs'." >&2
    exit 1
    ;;
esac

cd "$(dirname "$0")"
docker compose --profile "$TARGET" up --build
