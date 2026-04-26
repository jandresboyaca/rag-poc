FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml ./
RUN uv sync

COPY export_to_tensorboard.py ./

EXPOSE 6006

# ChromaDB is mounted read-only at /app/chroma_db.
# tensorboard_data is mounted as a writable volume to persist exports.
CMD ["sh", "-c", "uv run python export_to_tensorboard.py && uv run tensorboard --logdir ./tensorboard_data --port 6006 --host 0.0.0.0"]
