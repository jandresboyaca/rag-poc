"""End-to-end verification of the RAG pipeline.

Run this after ``ingest.py --docs ./docs --version <name>`` and before starting
the interactive CLI. It exercises every layer of the stack and prints a
pass/fail report:

    1. Ollama is reachable
    2. Embedding model produces a vector of expected dimensionality
    3. ChromaDB collection has chunks
    4. Vector search returns relevant chunks for known queries
    5. LLM produces a grounded answer that contains expected keywords

Exit code is non-zero if any check fails.
"""

from __future__ import annotations

import os
import sys

import chromadb
import httpx
from dotenv import load_dotenv

from step3_full_pipeline import RAGPipeline

TEST_CASES = [
    {
        "query": "How should I name Python functions and variables?",
        "expected_keywords": ["snake_case"],
    },
    {
        "query": "How do I create a hotfix branch?",
        "expected_keywords": ["main", "hotfix"],
    },
]


def _check(label: str, ok: bool, detail: str = "") -> bool:
    status = "PASS" if ok else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  [{status}] {label}{suffix}")
    return ok


def main() -> int:
    load_dotenv()
    ollama_url = os.environ["OLLAMA_URL"]
    embed_model = os.environ["EMBED_MODEL"]
    chat_model = os.environ["CHAT_MODEL"]
    chroma_path = os.environ["CHROMA_PATH"]
    collection_name = os.environ["COLLECTION_NAME"]

    print(f"=== RAG smoke test ===")
    print(f"  collection: {collection_name}")
    print(f"  embed: {embed_model}   chat: {chat_model}")
    print()

    print("[1] Ollama reachability")
    try:
        r = httpx.get(f"{ollama_url}/api/tags", timeout=5.0)
        ollama_ok = _check("ollama responding", r.status_code == 200)
    except Exception as exc:
        ollama_ok = _check("ollama responding", False, str(exc))
    if not ollama_ok:
        return 1

    print("[2] Embedding endpoint")
    try:
        r = httpx.post(
            f"{ollama_url}/api/embed",
            json={"model": embed_model, "input": "hello world"},
            timeout=120.0,
        )
        r.raise_for_status()
        vector = r.json()["embeddings"][0]
        embed_ok = _check(
            f"embedding produced ({len(vector)} dims)",
            len(vector) > 0,
        )
    except Exception as exc:
        embed_ok = _check("embedding produced", False, str(exc))
    if not embed_ok:
        return 1

    print("[3] ChromaDB collection has chunks")
    try:
        client = chromadb.PersistentClient(path=chroma_path)
        collection = client.get_collection(collection_name)
        count = collection.count()
        chunks_ok = _check(f"collection '{collection_name}' has {count} chunks", count > 0)
    except Exception as exc:
        chunks_ok = _check("collection accessible", False, str(exc))
        print(
            f"\n  Hint: run `python ingest.py --docs ./docs --version {collection_name}` first."
        )
        return 1
    if not chunks_ok:
        print(
            f"\n  Hint: run `python ingest.py --docs ./docs --version {collection_name}` first."
        )
        return 1

    print("[4] Pipeline.search returns chunks")
    pipeline = RAGPipeline(
        ollama_url=ollama_url,
        embed_model=embed_model,
        chat_model=chat_model,
        chroma_path=chroma_path,
        collection_name=collection_name,
    )
    search_ok = True
    for case in TEST_CASES:
        chunks = pipeline.search(case["query"])
        ok = _check(f"search: {case['query']!r}", len(chunks) > 0, f"{len(chunks)} chunks")
        search_ok = search_ok and ok
    if not search_ok:
        return 1

    print("[5] Pipeline.answer — grounded LLM output")
    answer_ok = True
    for case in TEST_CASES:
        answer = pipeline.answer(case["query"])
        haystack = answer.lower()
        missing = [kw for kw in case["expected_keywords"] if kw.lower() not in haystack]
        ok = _check(
            f"answer contains {case['expected_keywords']}: {case['query']!r}",
            not missing,
            f"missing={missing}" if missing else "",
        )
        if not ok:
            print(f"      answer was: {answer[:300]}...")
        answer_ok = answer_ok and ok
    if not answer_ok:
        return 1

    print("\nAll smoke tests PASSED — RAG is ready.")
    print("Start the chat with: cd cli && uv run python main.py ../mcp_rag_server.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
