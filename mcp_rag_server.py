"""MCP server exposing the RAG knowledge base as a single tool.

The CLI in ``cli/`` connects to this server over stdio. The chat LLM decides
when to call ``search_knowledge``; the answer it gets back is grounded in
the ChromaDB collection selected by ``COLLECTION_NAME`` in ``.env``.
"""

from __future__ import annotations

import sys

from mcp.server.fastmcp import FastMCP

from step2_query import build_rag_prompt, call_ollama_chat
from step3_full_pipeline import from_env

mcp = FastMCP("RAGKnowledgeBase", log_level="INFO")
pipeline = from_env()
print(
    f"[mcp_rag_server] Ready. collection={pipeline.collection_name} "
    f"chat={pipeline.chat_model} embed={pipeline.embed_model} "
    f"chroma_path={pipeline.chroma_path}",
    file=sys.stderr,
    flush=True,
)


@mcp.tool()
def search_knowledge(query: str) -> str:
    """Answer questions about the company's internal coding standards and engineering policy.

    WHEN TO USE: any question about naming conventions, function design rules,
    docstring format, error handling, imports, testing, code review, git
    branching, hotfix procedure, secrets management, dependency policy,
    incident classification, deployment policy, or documentation standards.
    The KB has authoritative answers — do not fall back to generic Python or
    industry advice.

    Args:
        query: A self-contained natural-language question in English.

    Returns:
        A grounded answer string built from the most relevant chunks. If
        nothing relevant is found, the answer says so — never fabricate policy.

    Examples:
        - "How should I name Python functions?"
        - "What is the hotfix branching policy?"
        - "When can I deploy to production?"
    """
    print(f"[mcp_rag_server] search_knowledge called: {query!r}", file=sys.stderr, flush=True)
    chunks = pipeline.search(query)
    print(
        f"[mcp_rag_server]   retrieved {len(chunks)} chunk(s); "
        f"first source preview: {(chunks[0][:80] + '...') if chunks else '<none>'}",
        file=sys.stderr,
        flush=True,
    )
    prompt = build_rag_prompt(query, chunks)
    answer = call_ollama_chat(prompt, pipeline.ollama_url, pipeline.chat_model)
    print(
        f"[mcp_rag_server]   answer length: {len(answer)} chars",
        file=sys.stderr,
        flush=True,
    )
    return answer


@mcp.resource("rag://collection")
def active_collection() -> str:
    """Return the name of the currently active KB version."""
    return pipeline.collection_name


if __name__ == "__main__":
    mcp.run(transport="stdio")
