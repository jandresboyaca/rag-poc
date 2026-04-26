"""Step 1 — Ingestion (educational).

Walks through the ingestion side of a RAG pipeline:

    docs/  →  chunk_text()  →  embed_text()  →  ChromaDB.add()

The functions here are intentionally small and single-purpose so each piece
can be inspected on its own. The same logic is reused (in a class) by
``step3_full_pipeline.py``.

Local→GCP migration: ``chunk_text`` is identical in both worlds. ``embed_text``
swaps the Ollama HTTP call for a Vertex AI client; the function signature does
not change.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

import chromadb
import httpx
from dotenv import load_dotenv


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping character chunks (sliding window).

    Args:
        text: Raw document text.
        chunk_size: Target size in characters of each chunk.
        overlap: Number of characters shared between consecutive chunks.

    Returns:
        List of chunk strings. The last chunk may be shorter than ``chunk_size``.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be in [0, chunk_size)")

    chunks: list[str] = []
    start = 0
    step = chunk_size - overlap
    while start < len(text):
        chunks.append(text[start : start + chunk_size])
        start += step
    return chunks


def embed_text(text: str, ollama_url: str, model: str) -> list[float]:
    """Embed a single text into a dense vector via the Ollama embeddings API.

    Args:
        text: Text to embed.
        ollama_url: Base URL of the Ollama server (e.g. ``http://localhost:11434``).
        model: Embedding model name (e.g. ``qwen3-embedding:8b``).

    Returns:
        A list of floats representing the embedding vector.
    """
    response = httpx.post(
        f"{ollama_url}/api/embed",
        json={"model": model, "input": text},
        timeout=120.0,
    )
    response.raise_for_status()
    payload = response.json()
    return payload["embeddings"][0]


def _iter_documents(docs_dir: Path) -> Iterable[Path]:
    """Yield every ``.md`` and ``.txt`` file inside ``docs_dir`` (recursively)."""
    for ext in ("*.md", "*.txt"):
        yield from sorted(docs_dir.rglob(ext))


def ingest_documents(
    docs_dir: str,
    ollama_url: str,
    embed_model: str,
    chroma_path: str,
    collection_name: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> dict:
    """Read documents, chunk them, embed each chunk, and store them in ChromaDB.

    Args:
        docs_dir: Directory containing ``.md``/``.txt`` documents.
        ollama_url: Ollama base URL.
        embed_model: Embedding model identifier.
        chroma_path: Filesystem path where ChromaDB persists data.
        collection_name: Name of the collection (one logical "version" of the KB).
        chunk_size: Chunk size passed to :func:`chunk_text`.
        chunk_overlap: Overlap passed to :func:`chunk_text`.

    Returns:
        Dict with statistics: ``files``, ``chunks``, ``collection``.
    """
    path = Path(docs_dir)
    if not path.is_dir():
        raise FileNotFoundError(f"docs directory does not exist: {path}")

    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    files = list(_iter_documents(path))
    total_chunks = 0
    for file_path in files:
        text = file_path.read_text(encoding="utf-8")
        chunks = chunk_text(text, chunk_size=chunk_size, overlap=chunk_overlap)
        if not chunks:
            continue
        ids = [f"{file_path.name}_chunk_{i}" for i in range(len(chunks))]
        embeddings = [embed_text(c, ollama_url, embed_model) for c in chunks]
        metadatas = [
            {"source": file_path.name, "chunk_index": i, "version": collection_name}
            for i in range(len(chunks))
        ]
        collection.upsert(
            ids=ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        total_chunks += len(chunks)
        print(f"  {file_path.name}: {len(chunks)} chunks")

    return {
        "files": len(files),
        "chunks": total_chunks,
        "collection": collection_name,
    }


if __name__ == "__main__":
    load_dotenv()
    stats = ingest_documents(
        docs_dir="./docs",
        ollama_url=os.environ["OLLAMA_URL"],
        embed_model=os.environ["EMBED_MODEL"],
        chroma_path=os.environ["CHROMA_PATH"],
        collection_name=os.environ["COLLECTION_NAME"],
    )
    print(
        f"\nIngested {stats['chunks']} chunks from {stats['files']} files "
        f"into collection '{stats['collection']}'"
    )
