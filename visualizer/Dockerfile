FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml ./

# Create a .venv and install deps explicitly. Using `uv pip install .` instead
# of `uv sync` so the build does not depend on a lockfile.
RUN uv venv && uv pip install --no-cache .

COPY export_to_tensorboard.py ./

EXPOSE 6006

# chroma_db and tensorboard_data are mounted as volumes from docker-compose.
CMD ["sh", "-c", "uv run python export_to_tensorboard.py && uv run tensorboard --logdir ./tensorboard_data --port 6006 --host 0.0.0.0"]
