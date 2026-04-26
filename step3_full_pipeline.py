"""Step 3 — Full pipeline (reusable class).

Wraps the helpers from step1/step2 in a single ``RAGPipeline`` class with one
persistent ChromaDB client. This is the object the MCP server, the smoke
test, and ``ingest.py`` consume.

The interface (``ingest`` / ``search`` / ``answer``) is the contract that does
not change when migrating local→GCP. Replacing Ollama with Vertex AI happens
inside the methods, not at the call sites.
"""

from __future__ import annotations

import os
from pathlib import Path

import chromadb
from dotenv import load_dotenv

from step1_ingestion import chunk_text, embed_text, _iter_documents
from step2_query import build_rag_prompt, call_ollama_chat


class RAGPipeline:
    """End-to-end RAG pipeline for one ChromaDB collection (one KB version)."""

    def __init__(
        self,
        ollama_url: str,
        embed_model: str,
        chat_model: str,
        chroma_path: str,
        collection_name: str,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        n_results: int = 5,
    ) -> None:
        self.ollama_url = ollama_url
        self.embed_model = embed_model
        self.chat_model = chat_model
        self.chroma_path = chroma_path
        self.collection_name = collection_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.n_results = n_results

        self._client = chromadb.PersistentClient(path=chroma_path)
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def ingest(self, docs_dir: str) -> dict:
        """Chunk + embed + upsert every document under ``docs_dir`` into the collection."""
        path = Path(docs_dir)
        if not path.is_dir():
            raise FileNotFoundError(f"docs directory does not exist: {path}")

        files = list(_iter_documents(path))
        total_chunks = 0
        for file_path in files:
            text = file_path.read_text(encoding="utf-8")
            chunks = chunk_text(text, self.chunk_size, self.chunk_overlap)
            if not chunks:
                continue
            ids = [f"{file_path.name}_chunk_{i}" for i in range(len(chunks))]
            embeddings = [
                embed_text(c, self.ollama_url, self.embed_model) for c in chunks
            ]
            metadatas = [
                {
                    "source": file_path.name,
                    "chunk_index": i,
                    "version": self.collection_name,
                }
                for i in range(len(chunks))
            ]
            self._collection.upsert(
                ids=ids,
                documents=chunks,
                embeddings=embeddings,
                metadatas=metadatas,
            )
            total_chunks += len(chunks)

        return {
            "files": len(files),
            "chunks": total_chunks,
            "collection": self.collection_name,
        }

    def search(self, query: str) -> list[str]:
        """Return the top-N most similar chunks for ``query``."""
        query_embedding = embed_text(query, self.ollama_url, self.embed_model)
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=self.n_results,
        )
        return results["documents"][0] if results["documents"] else []

    def answer(self, query: str) -> str:
        """Search + build prompt + call LLM. Returns the grounded answer text."""
        chunks = self.search(query)
        prompt = build_rag_prompt(query, chunks)
        return call_ollama_chat(prompt, self.ollama_url, self.chat_model)


def from_env(collection_name: str | None = None) -> RAGPipeline:
    """Build a ``RAGPipeline`` from environment variables (loads ``.env``).

    If ``collection_name`` is given it overrides ``COLLECTION_NAME`` from the env;
    this is how callers select a specific KB version.
    """
    rag_root = Path(__file__).resolve().parent
    load_dotenv(rag_root / ".env")

    chroma_path = Path(os.environ["CHROMA_PATH"])
    if not chroma_path.is_absolute():
        chroma_path = (rag_root / chroma_path).resolve()

    return RAGPipeline(
        ollama_url=os.environ["OLLAMA_URL"],
        embed_model=os.environ["EMBED_MODEL"],
        chat_model=os.environ["CHAT_MODEL"],
        chroma_path=str(chroma_path),
        collection_name=collection_name or os.environ["COLLECTION_NAME"],
    )
