"""MCP server exposing the RAG knowledge base as a single tool.

The CLI in ``cli/`` connects to this server over stdio. The chat LLM decides
when to call ``search_knowledge``; the answer it gets back is grounded in
the ChromaDB collection selected by ``COLLECTION_NAME`` in ``.env``.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from step3_full_pipeline import from_env

mcp = FastMCP("RAGKnowledgeBase", log_level="ERROR")
pipeline = from_env()


@mcp.tool()
def search_knowledge(query: str) -> str:
    """Search the internal knowledge base (coding standards, engineering policy).

    Returns a grounded answer based on the documents indexed in ChromaDB.
    Use this whenever the user asks about internal standards, policies,
    branching rules, code review, deployment, secrets, or incident handling.
    """
    return pipeline.answer(query)


@mcp.resource("rag://collection")
def active_collection() -> str:
    """Return the name of the currently active KB version."""
    return pipeline.collection_name


if __name__ == "__main__":
    mcp.run(transport="stdio")
