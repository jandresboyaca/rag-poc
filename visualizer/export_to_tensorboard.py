"""Export a ChromaDB collection to the TensorBoard Projector format.

Each version of the knowledge base (one ChromaDB collection) becomes one
subdirectory under ``tensorboard_data/<version>/`` containing:

    vectors.tsv             — one row per chunk, tab-separated float values
    metadata.tsv            — header + one row per chunk (chunk_id, source, version, preview)
    projector_config.pbtxt  — points TensorBoard at the two TSV files

Usage::

    python export_to_tensorboard.py
    python export_to_tensorboard.py --version v2-add-security-policy
    python export_to_tensorboard.py --list-versions
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import chromadb
from dotenv import load_dotenv


def list_versions(chroma_path: str) -> int:
    client = chromadb.PersistentClient(path=chroma_path)
    collections = client.list_collections()
    if not collections:
        print("(no collections — run ingest.py first)")
        return 0
    print(f"{'VERSION':40s} {'CHUNKS':>8s}")
    print("-" * 50)
    for coll in collections:
        c = client.get_collection(coll.name)
        print(f"{coll.name:40s} {c.count():>8d}")
    return 0


def export(chroma_path: str, version: str, output_root: Path) -> int:
    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_collection(version)
    data = collection.get(include=["embeddings", "documents", "metadatas"])

    # ChromaDB returns embeddings as a numpy array — avoid `or []` because
    # numpy raises ValueError when truth-testing arrays.
    embeddings = data.get("embeddings")
    if embeddings is None:
        embeddings = []
    documents = data.get("documents") if data.get("documents") is not None else []
    metadatas = data.get("metadatas") if data.get("metadatas") is not None else []
    ids = data.get("ids") if data.get("ids") is not None else []

    if len(embeddings) == 0:
        print(f"Collection '{version}' is empty.")
        return 1

    dims = len(embeddings[0])
    print(f"Connected to ChromaDB. Collection '{version}': {len(embeddings)} vectors ({dims} dims)")

    out_dir = output_root / version
    out_dir.mkdir(parents=True, exist_ok=True)

    vectors_path = out_dir / "vectors.tsv"
    with vectors_path.open("w", encoding="utf-8") as f:
        for vec in embeddings:
            f.write("\t".join(f"{v:.6f}" for v in vec))
            f.write("\n")
    print(f"Written: {vectors_path.relative_to(output_root.parent)}")

    metadata_path = out_dir / "metadata.tsv"
    with metadata_path.open("w", encoding="utf-8") as f:
        f.write("chunk_id\tsource\tversion\tpreview\n")
        for cid, doc, meta in zip(ids, documents, metadatas):
            preview = (doc or "").replace("\t", " ").replace("\n", " ")[:80]
            source = (meta or {}).get("source", "")
            ver = (meta or {}).get("version", version)
            f.write(f"{cid}\t{source}\t{ver}\t{preview}\n")
    print(f"Written: {metadata_path.relative_to(output_root.parent)}")

    # TensorBoard Projector reads projector_config.pbtxt from the logdir root
    # (not from subfolders). Aggregate every version that has been exported so
    # far into one config so the UI lets you switch between them.
    _rewrite_root_projector_config(output_root)

    print("\nOpen in browser: http://localhost:6006/#projector")
    return 0


def _rewrite_root_projector_config(output_root: Path) -> None:
    """Scan ``output_root`` for every version subfolder that has both TSVs and
    write a single ``projector_config.pbtxt`` at the root listing them all."""
    blocks: list[str] = []
    for version_dir in sorted(p for p in output_root.iterdir() if p.is_dir()):
        vectors = version_dir / "vectors.tsv"
        metadata = version_dir / "metadata.tsv"
        if not vectors.exists() or not metadata.exists():
            continue
        name = version_dir.name
        blocks.append(
            "embeddings {\n"
            f'  tensor_name: "{name}"\n'
            f'  tensor_path: "{name}/vectors.tsv"\n'
            f'  metadata_path: "{name}/metadata.tsv"\n'
            "}\n"
        )
    root_config = output_root / "projector_config.pbtxt"
    root_config.write_text("".join(blocks), encoding="utf-8")
    print(f"Written: {root_config.relative_to(output_root.parent)} ({len(blocks)} version(s))")


def main() -> int:
    # Resolve paths relative to this file so the script works no matter the cwd.
    here = Path(__file__).resolve().parent
    rag_root = here.parent
    load_dotenv(rag_root / ".env")

    chroma_path = os.environ.get("CHROMA_PATH")
    if not chroma_path or chroma_path.startswith("./") or chroma_path == "chroma_db":
        chroma_path = str(rag_root / "chroma_db")
    default_version = os.environ.get("COLLECTION_NAME", "knowledge_base")
    print(f"Using chroma_path: {chroma_path}")

    parser = argparse.ArgumentParser(description="Export ChromaDB to TensorBoard Projector")
    parser.add_argument(
        "--version",
        default=default_version,
        help=f"Collection name to export (default: {default_version})",
    )
    parser.add_argument(
        "--list-versions",
        action="store_true",
        help="List collections available in ChromaDB and exit",
    )
    parser.add_argument(
        "--output",
        default="./tensorboard_data",
        help="Output root directory (default: ./tensorboard_data)",
    )
    args = parser.parse_args()

    if args.list_versions:
        return list_versions(chroma_path)

    output_root = Path(args.output)
    output_root.mkdir(parents=True, exist_ok=True)
    return export(chroma_path, args.version, output_root)


if __name__ == "__main__":
    sys.exit(main())
