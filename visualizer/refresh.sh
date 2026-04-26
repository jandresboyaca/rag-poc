#!/usr/bin/env bash
# refresh.sh — Re-export ChromaDB to TensorBoard after ingesting a new version.
# Usage:
#   bash refresh.sh           # exports COLLECTION_NAME from ../.env
#   bash refresh.sh v2        # exports a specific version

set -e

VERSION=${1:-""}

if [ -n "$VERSION" ]; then
  echo "Exporting version: $VERSION"
  uv run python export_to_tensorboard.py --version "$VERSION"
else
  echo "Exporting default version (from .env)"
  uv run python export_to_tensorboard.py
fi

echo ""
echo "TensorBoard data updated."
echo "If TensorBoard is running, refresh the browser at: http://localhost:6006/#projector"
echo "If not running:  uv run tensorboard --logdir ./tensorboard_data --port 6006"
