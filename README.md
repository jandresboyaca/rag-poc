# RAG PoC — Local Stack (Ollama + ChromaDB + MCP)

Step-by-step Retrieval-Augmented Generation proof of concept. Runs **fully local**
on Ollama and ChromaDB, exposed to a terminal chat via MCP. The architecture is
designed so the migration to GCP Vertex AI is a **swap of components, not a rewrite**.

Knowledge base: internal coding standards (`docs/coding_standards.md`) and
engineering policy (`docs/engineering_policy.md`).

---

## 1. Architecture Overview

See `.doc/rag_mcp_architecture_detailed.svg` and `.doc/chatbot_rag_mcp_architecture.svg`
for the full diagrams.

### Query flow (every user question)

```
User question (terminal CLI)
        │
        ▼  via MCP stdio
mcp_rag_server.py  →  RAGPipeline.answer(query)
        │
        ├─ 1. embed_text(query)         qwen3-embedding:8b  via Ollama /api/embed
        ├─ 2. vector search             ChromaDB cosine similarity, top-5 chunks
        ├─ 3. build_rag_prompt          system + chunks + question (fixed template)
        └─ 4. LLM generation            neural-chat        via Ollama /api/chat
        │
        ▼
grounded answer  →  MCP server  →  CLI
```

### Ingestion flow (runs once per KB version)

```
docs/  →  chunk_text(size=500, overlap=50)  →  embed_text  →  ChromaDB.upsert
```

---

## 2. RAG Type: Dense Retrieval

| Type        | How it works                  | Best for                                    |
|-------------|-------------------------------|---------------------------------------------|
| **Dense** ✅ | Vectors + semantic similarity | Meaning-based questions, paraphrases        |
| Sparse      | Keyword matching (BM25)       | Exact terms, codes, IDs                     |
| Hybrid      | Dense + Sparse combined       | Production systems, best recall + precision |

**Why Dense for this PoC:** asking *"How should I handle errors?"* still finds the
chunk that talks about *exception handling* — the model understands meaning,
not just keywords.

---

## 3. Embedding Model: `qwen3-embedding:8b` (Q4_K_M)

- Dedicated embedding model — its **only** job is converting text into a 4096-dim vector.
- 8B parameters quantized to Q4_K_M: fits in **~5 GB VRAM**. Your 12 GB GPU has room
  for the chat LLM on top.
- State-of-the-art quality for English technical retrieval.
- **Do not** use `neural-chat` for embeddings — chat-tuned LLMs produce less
  precise semantic vectors because they were not trained for retrieval.

| Model                       | Dims | VRAM    | Notes                                |
|-----------------------------|------|---------|--------------------------------------|
| `qwen3-embedding:8b` Q4_K_M | 4096 | ~5 GB   | State-of-the-art ← **we use this**   |
| `bge-m3`                    | 1024 | 1.5 GB  | Strong, multilingual                 |
| `mxbai-embed-large`         | 1024 | 670 MB  | Good, English                        |
| `nomic-embed-text`          | 768  | 274 MB  | Baseline                             |

---

## 4. Local Stack vs Vertex AI

See `.doc/local_vs_vertex_english.svg`.

| Layer       | Local (this PoC)                     | GCP (next step)                   |
|-------------|--------------------------------------|-----------------------------------|
| Embeddings  | `qwen3-embedding:8b` (Ollama)        | `text-embedding-004` (Vertex AI)  |
| Vector DB   | ChromaDB on disk                     | Vertex AI Vector Search           |
| LLM         | `neural-chat` (Ollama)               | Gemini Pro / Gemini Flash         |
| Infra       | Your machine                         | GCP (monitoring, IAM included)    |

**What does NOT change:** `chunk_text()`, `build_rag_prompt()`, the `RAGPipeline`
interface, and `mcp_rag_server.py`. The local→GCP swap only touches the
embedding and chat client implementations.

---

## 5. Project Layout

```
RAG/
├── setup.sh              prerequisites: Ollama check, model pulls, deps
├── smoke_test.py         end-to-end pass/fail check
├── pyproject.toml        chromadb, httpx, mcp[cli], python-dotenv
├── .env                  OLLAMA_URL, EMBED_MODEL, CHAT_MODEL, COLLECTION_NAME
├── docs/                 knowledge base (coding standards + policy)
├── chroma_db/            auto-created on first ingest
├── ingest.py             versioned KB CLI (--docs / --list / --inspect / --delete)
├── step1_ingestion.py    educational: chunk + embed + store
├── step2_query.py        educational: embed query + search + LLM
├── step3_full_pipeline.py  RAGPipeline class (used everywhere)
├── mcp_rag_server.py     MCP server exposing search_knowledge
├── cli/                  terminal chat interface (moved from cli_project/)
└── visualizer/           TensorBoard Projector sub-project, Dockerized
```

---

## 6. Setup

```bash
# 0. Initialize git (one-time, from RAG/)
git init && git add . && git commit -m "chore: initial RAG project structure"

# 1. Prerequisites — pulls models if missing, installs deps for all sub-projects
bash setup.sh

# 2. Ingest documents into a named version
uv run python ingest.py --docs ./docs --version v1
uv run python ingest.py --list

# 3. End-to-end check
uv run python smoke_test.py

# 4. (Optional) Visualize embeddings in TensorBoard Projector
cd visualizer
docker compose up           # http://localhost:6006/#projector
# expect two clusters: coding_standards.md vs engineering_policy.md

# 5. Standalone query (no chat UI)
cd ..
uv run python step2_query.py "How should I name my Python variables?"
uv run python step2_query.py "How do I create a hotfix branch?"

# 6. Interactive terminal chat with RAG attached
cd cli
uv run python main.py ../mcp_rag_server.py
# Try: "How should I handle errors in Python?" — the LLM calls search_knowledge
```

> If `COLLECTION_NAME` in `.env` is `knowledge_base`, your ingest version must
> also be `knowledge_base` (or change the env var to point at any other version
> like `v1`, `v2-add-security-policy`, etc.).

---

## 7. Versioned Knowledge Base

Each call to `ingest.py --version <name>` is a separate ChromaDB collection.
Multiple versions live side-by-side:

```bash
uv run python ingest.py --docs ./docs           --version v1
uv run python ingest.py --docs ./docs/security  --version v2-add-security-policy
uv run python ingest.py --list
uv run python ingest.py --inspect v1
uv run python ingest.py --delete v1
```

Switch which version the MCP server (and CLI chat) uses by setting
`COLLECTION_NAME=v2-add-security-policy` in `.env` before starting the server.

After a new ingest, refresh TensorBoard:

```bash
cd visualizer
bash refresh.sh v2-add-security-policy
```

---

## 8. End-to-End Data Flow

```
User in CLI: "How should I handle errors in Python?"
    │
    ▼
CliChat → Chat.run() → neural-chat receives tools=[search_knowledge]
    │
    ▼  LLM decides to call the tool
ToolManager → rag_client.call_tool("search_knowledge", {"query": "..."})
    │
    ▼  stdio pipe
mcp_rag_server.py → RAGPipeline.answer("...")
    │  1. embed_text(query)            → 4096-dim vector
    │  2. ChromaDB.query(vector, n=5)  → top chunks from coding_standards.md
    │  3. build_rag_prompt(query, chunks)
    │  4. call_ollama_chat(prompt, "neural-chat")
    ▼
"Always catch specific exceptions. Log with context (user_id, request_id).
 Never use bare except."
    │
    ▼  tool_result → second LLM call → final answer printed in CLI
```

---

## 9. Verification Checklist

- [ ] `bash setup.sh` finishes clean
- [ ] `uv run python ingest.py --docs ./docs --version knowledge_base` reports N chunks
- [ ] `uv run python ingest.py --list` shows the version
- [ ] `uv run python smoke_test.py` → all checks PASS
- [ ] `uv run python step2_query.py "How do I name variables?"` references coding_standards.md
- [ ] `uv run python step2_query.py "How do I create a hotfix?"` references engineering_policy.md
- [ ] `cd visualizer && docker compose up` opens TensorBoard at `localhost:6006/#projector`
- [ ] Two semantic clusters visible (coding standards vs engineering policy)
- [ ] `cd cli && uv run python main.py ../mcp_rag_server.py` starts CLI with both MCP servers
- [ ] Question in CLI → LLM calls `search_knowledge` → answer grounded in the docs
