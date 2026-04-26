# MCP Inspector — Visual debugger for the project's MCP servers

Web UI to click through the tools, resources, and prompts exposed by either
of the project's MCP servers — without going through the CLI chat. Useful to
verify docstrings render correctly, manually call tools with crafted inputs,
and watch the request/response payloads.

Powered by the official [`@modelcontextprotocol/inspector`](https://github.com/modelcontextprotocol/inspector)
(Node), wrapped in a Docker image that also carries Python + `uv` so it can
spawn the project's MCP servers as subprocesses over stdio.

---

## Prerequisites

- Docker + Docker Compose
- The RAG project mounted at `..` (the inspector binds it via volume)

No Node, no Python, and no `uv` need to be installed on the host — everything
runs inside the container.

---

## Usage

Pick which server to inspect:

```bash
# RAG knowledge base server (search_knowledge tool, rag://collection resource)
bash launch.sh rag

# Document MCP server (read_doc + edit_doc tools, docs://documents resource)
bash launch.sh docs
```

Then open the UI: **http://localhost:6274**

The inspector connects automatically to the spawned server — you should see:
- **Tools** tab — list of `@mcp.tool()` functions with rendered docstrings
- **Resources** tab — `@mcp.resource()` URIs and their contents
- **Prompts** tab — `@mcp.prompt()` templates (currently empty in both servers)

Click any tool, fill the input form, hit *Run*, and inspect the JSON response.

Stop with `Ctrl+C`. To switch servers, stop the running profile and launch
the other one (both bind to the same ports).

---

## Auth

For convenience the compose file sets `DANGEROUSLY_OMIT_AUTH=true` so the UI
loads without entering an auth token. This is a **local-only debug tool** —
do not expose port 6274 to a network you do not trust.

If you want auth on, remove the `DANGEROUSLY_OMIT_AUTH` env var. The token
will be printed in the container logs each launch; copy-paste it in the UI.

---

## Files

- `Dockerfile` — Node 20 + Python + uv image
- `docker-compose.yml` — two profiles, one per target server
- `launch.sh` — convenience wrapper for `docker compose --profile X up --build`
