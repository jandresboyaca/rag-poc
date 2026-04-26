"""Step 2 — Query (educational).

Given a user question:

    1. Embed the question.
    2. Search ChromaDB for the top-N most similar chunks.
    3. Build a grounded prompt that includes those chunks as context.
    4. Ask the local LLM (Ollama) to answer using only that context.

Local→GCP migration: ``build_rag_prompt`` is identical. ``call_ollama_chat``
swaps for a Gemini client; ``search_similar_chunks`` swaps ChromaDB for
Vertex AI Vector Search. Function signatures do not change.
"""

from __future__ import annotations

import os
import sys

import chromadb
import httpx
from dotenv import load_dotenv

from step1_ingestion import embed_text


def search_similar_chunks(
    query: str,
    collection: chromadb.api.models.Collection.Collection,
    ollama_url: str,
    embed_model: str,
    n_results: int = 5,
) -> tuple[list[str], list[float]]:
    """Embed ``query`` and return the top-N most similar chunks from ``collection``.

    Returns:
        Tuple ``(chunks, distances)``. Lower distance is closer (cosine).
    """
    query_embedding = embed_text(query, ollama_url, embed_model)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
    )
    chunks = results["documents"][0] if results["documents"] else []
    distances = results["distances"][0] if results.get("distances") else []
    return chunks, distances


def build_rag_prompt(query: str, chunks: list[str]) -> str:
    """Assemble the grounded prompt that the LLM will see.

    The template is intentionally fixed — it does not change between local and
    GCP. Tweaking it is fine; per-environment branching is not.
    """
    context_block = "\n\n---\n\n".join(chunks) if chunks else "(no context available)"
    return (
        "You are a helpful assistant for an internal engineering team. "
        "Answer the question using ONLY the context below. "
        "If the answer is not in the context, say you do not know.\n\n"
        "Context:\n"
        f"{context_block}\n\n"
        f"Question: {query}\n"
        "Answer:"
    )


def call_ollama_chat(prompt: str, ollama_url: str, model: str) -> str:
    """Send ``prompt`` to the Ollama chat endpoint and return the assistant text."""
    response = httpx.post(
        f"{ollama_url}/api/chat",
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        },
        timeout=300.0,
    )
    response.raise_for_status()
    return response.json()["message"]["content"]


def main(query: str) -> None:
    load_dotenv()
    ollama_url = os.environ["OLLAMA_URL"]
    embed_model = os.environ["EMBED_MODEL"]
    chat_model = os.environ["CHAT_MODEL"]
    chroma_path = os.environ["CHROMA_PATH"]
    collection_name = os.environ["COLLECTION_NAME"]

    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_collection(collection_name)

    chunks, distances = search_similar_chunks(
        query, collection, ollama_url, embed_model, n_results=5
    )

    print(f"\n=== Query ===\n{query}\n")
    print("=== Retrieved chunks (lower distance = closer) ===")
    for i, (chunk, dist) in enumerate(zip(chunks, distances)):
        preview = chunk.replace("\n", " ")[:120]
        print(f"[{i}] dist={dist:.4f}  {preview}...")

    prompt = build_rag_prompt(query, chunks)
    answer = call_ollama_chat(prompt, ollama_url, chat_model)
    print("\n=== Answer ===")
    print(answer)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python step2_query.py "your question here"')
        sys.exit(1)
    main(" ".join(sys.argv[1:]))
