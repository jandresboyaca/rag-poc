"""Versioned ingestion CLI for the RAG knowledge base.

Each `--version` is a separate ChromaDB collection. You can have multiple
versions side-by-side and point the MCP server at any one of them via the
``COLLECTION_NAME`` environment variable.

Examples::

    python ingest.py --docs ./docs --version v1
    python ingest.py --list
    python ingest.py --inspect v1
    python ingest.py --delete v1
"""

from __future__ import annotations

import argparse
import os
import sys

import chromadb
from dotenv import load_dotenv

from step3_full_pipeline import RAGPipeline


def _client(chroma_path: str) -> chromadb.PersistentClient:
    return chromadb.PersistentClient(path=chroma_path)


def cmd_ingest(docs_dir: str, version: str) -> int:
    pipeline = RAGPipeline(
        ollama_url=os.environ["OLLAMA_URL"],
        embed_model=os.environ["EMBED_MODEL"],
        chat_model=os.environ["CHAT_MODEL"],
        chroma_path=os.environ["CHROMA_PATH"],
        collection_name=version,
    )
    print(f"Ingesting '{docs_dir}' into collection '{version}'...")
    stats = pipeline.ingest(docs_dir)
    print(
        f"\nDone. Collection '{stats['collection']}': "
        f"{stats['chunks']} chunks from {stats['files']} files."
    )
    return 0


def cmd_list(chroma_path: str) -> int:
    client = _client(chroma_path)
    collections = client.list_collections()
    if not collections:
        print("(no collections yet — run --docs ... --version <name> first)")
        return 0
    print(f"{'VERSION':40s} {'CHUNKS':>8s}")
    print("-" * 50)
    for coll in collections:
        c = client.get_collection(coll.name)
        print(f"{coll.name:40s} {c.count():>8d}")
    return 0


def cmd_delete(version: str, chroma_path: str) -> int:
    client = _client(chroma_path)
    client.delete_collection(version)
    print(f"Deleted collection '{version}'.")
    return 0


def cmd_inspect(version: str, chroma_path: str) -> int:
    client = _client(chroma_path)
    collection = client.get_collection(version)
    total = collection.count()
    print(f"Collection '{version}': {total} chunks")
    if total == 0:
        return 0
    sample = collection.peek(limit=5)
    print("\nFirst 5 chunks:")
    for i, (cid, doc, meta) in enumerate(
        zip(sample["ids"], sample["documents"], sample["metadatas"])
    ):
        preview = doc.replace("\n", " ")[:100]
        print(f"  [{i}] {cid}  source={meta.get('source')}")
        print(f"      {preview}...")
    return 0


def main() -> int:
    load_dotenv()
    chroma_path = os.environ.get("CHROMA_PATH", "./chroma_db")

    parser = argparse.ArgumentParser(description="RAG knowledge base ingestion tool")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--docs", help="Directory with .md/.txt documents to ingest")
    group.add_argument("--list", action="store_true", help="List all collections")
    group.add_argument("--delete", metavar="VERSION", help="Delete a collection")
    group.add_argument("--inspect", metavar="VERSION", help="Show first chunks of a collection")
    parser.add_argument(
        "--version",
        help="Collection name (required with --docs). Example: v1-coding-standards",
    )
    args = parser.parse_args()

    if args.docs:
        if not args.version:
            parser.error("--version is required when using --docs")
        return cmd_ingest(args.docs, args.version)
    if args.list:
        return cmd_list(chroma_path)
    if args.delete:
        return cmd_delete(args.delete, chroma_path)
    if args.inspect:
        return cmd_inspect(args.inspect, chroma_path)
    return 1


if __name__ == "__main__":
    sys.exit(main())
