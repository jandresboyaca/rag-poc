FROM node:20-slim

# Python + uv are needed because the MCP Inspector spawns the MCP servers as
# subprocesses, and our servers run on Python via uv (the inspector itself is
# Node, but the protocol it speaks goes over stdio to the spawned process).
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        python3 python3-venv curl ca-certificates \
 && curl -LsSf https://astral.sh/uv/install.sh | sh \
 && ln -s /root/.local/bin/uv /usr/local/bin/uv \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Inspector default ports:
#   6274 — Web UI
#   6277 — Proxy that pipes UI <-> stdio MCP server
EXPOSE 6274 6277

# TARGET picks which server to inspect: 'rag' (RAG knowledge base) or
# 'docs' (in-memory document store). Set via docker-compose service.
ENV TARGET=rag

CMD ["sh", "-c", "\
  if [ \"$TARGET\" = 'rag' ]; then \
    npx -y @modelcontextprotocol/inspector \
      uv run --project /workspace python /workspace/mcp_rag_server.py; \
  else \
    npx -y @modelcontextprotocol/inspector \
      uv run --project /workspace/cli python /workspace/cli/mcp_server.py; \
  fi"]
