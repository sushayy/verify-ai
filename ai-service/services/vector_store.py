"""Persistent ChromaDB vector store over the curated reference corpus.

Replaces the in-memory numpy index the original CLI rebuilt on every run
(`verify_ai/retrieve.py`): the corpus is embedded once into `chroma_db/` and
reused across requests and restarts.

Embeddings use Chroma's bundled ONNX model (all-MiniLM-L6-v2), so ingest and
search cost no API quota and work with no network access.
"""

import json
import os
import re

import chromadb

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_CORPUS_DIR = os.path.join(_BASE_DIR, "corpus")
_DEFAULT_DB_PATH = os.path.join(_BASE_DIR, "chroma_db")
_COLLECTION_NAME = "reference_corpus"

# Target characters per chunk — the original CLI's 500, but packed to
# sentence boundaries rather than sliced blindly.
_CHUNK_SIZE = 500

# Maximum L2 distance for a hit to count as relevant. Measured against this
# corpus, on-topic matches land under 0.9 and off-topic ones above 1.3, so
# this cleanly drops the near-random filler that padded early results.
MAX_DISTANCE = 1.2

_collection = None


def _chunk_text(text: str, size: int = _CHUNK_SIZE) -> list[str]:
    """Splits text into chunks of whole sentences.

    The original CLI cut every `size` characters, which split words in half
    mid-chunk and made retrieved evidence read badly. This packs whole
    sentences up to the size limit instead, and normalizes the hard line
    wrapping in the corpus files into single-spaced prose.

    Args:
        text: The text to split.
        size: Target maximum characters per chunk. A single sentence longer
            than this becomes its own oversized chunk rather than being cut.

    Returns:
        Non-empty chunks, each a run of complete sentences.
    """
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        sentence = " ".join(sentence.split())
        if not sentence:
            continue
        if current and len(current) + 1 + len(sentence) > size:
            chunks.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        chunks.append(current)
    return chunks


def get_collection(db_path: str = _DEFAULT_DB_PATH):
    """Returns the reference-corpus collection, creating it if needed.

    The client is cached module-level so repeated requests reuse one
    connection and one loaded embedding model.

    Args:
        db_path: Directory the persistent Chroma database lives in.

    Returns:
        The `reference_corpus` Chroma collection.
    """
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=db_path)
        _collection = client.get_or_create_collection(name=_COLLECTION_NAME)
    return _collection


def _load_sources(corpus_dir: str) -> dict:
    """Loads the corpus metadata sidecar mapping filenames to source details.

    Args:
        corpus_dir: Directory holding the corpus and its `sources.json`.

    Returns:
        A mapping of filename to its metadata dict. Empty if the sidecar is
        absent, so an undocumented corpus still ingests.
    """
    path = os.path.join(corpus_dir, "sources.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def ingest_corpus(corpus_dir: str = _DEFAULT_CORPUS_DIR, db_path: str = _DEFAULT_DB_PATH) -> int:
    """Embeds every `.txt` document in the corpus into the vector store.

    Idempotent: chunk ids are derived from filename and position, so
    re-running updates existing chunks in place rather than duplicating
    them. Safe to call on every service startup.

    Args:
        corpus_dir: Directory of reference `.txt` documents.
        db_path: Directory the persistent Chroma database lives in.

    Returns:
        The number of chunks ingested.
    """
    collection = get_collection(db_path)
    sources = _load_sources(corpus_dir)

    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict] = []

    for filename in sorted(os.listdir(corpus_dir)):
        if not filename.endswith(".txt"):
            continue
        with open(os.path.join(corpus_dir, filename), encoding="utf-8") as f:
            text = f.read()
        source = sources.get(filename, {})
        for i, chunk in enumerate(_chunk_text(text)):
            ids.append(f"{filename}:{i}")
            documents.append(chunk)
            # Chroma rejects None metadata values, so every field gets a
            # concrete default.
            metadatas.append(
                {
                    "filename": filename,
                    "title": source.get("title", filename.removesuffix(".txt")),
                    "url": source.get("url", ""),
                    "publisher": source.get("publisher", ""),
                    "reliability": float(source.get("reliability", 0.7)),
                }
            )

    if ids:
        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

    # Drop chunks that no longer exist, so editing or deleting a corpus
    # document doesn't leave orphaned embeddings behind.
    stale = set(collection.get(include=[])["ids"]) - set(ids)
    if stale:
        collection.delete(ids=list(stale))

    return len(ids)


def query(
    text: str,
    k: int = 4,
    db_path: str = _DEFAULT_DB_PATH,
    max_distance: float = MAX_DISTANCE,
) -> list[dict]:
    """Finds the corpus chunks most semantically similar to a query.

    Args:
        text: The query text, normally a claim's normalized statement.
        k: Maximum number of chunks to return.
        db_path: Directory the persistent Chroma database lives in.
        max_distance: Drop hits further away than this. Without it the
            search always returns `k` rows, so a claim the corpus knows
            nothing about comes back padded with unrelated documents.

    Returns:
        Up to `k` dicts with `document`, `metadata`, and `distance` keys,
        nearest first. Empty if the store is unpopulated or nothing is
        relevant enough.
    """
    collection = get_collection(db_path)
    count = collection.count()
    if count == 0:
        return []

    results = collection.query(query_texts=[text], n_results=min(k, count))
    return [
        {"document": doc, "metadata": meta, "distance": dist}
        for doc, meta, dist in zip(
            results["documents"][0], results["metadatas"][0], results["distances"][0]
        )
        if dist <= max_distance
    ]
