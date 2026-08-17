"""Persistent ChromaDB vector store over the curated reference corpus.

Replaces the in-memory numpy index the original CLI rebuilt on every run
(`verify_ai/retrieve.py`): the corpus is embedded once into `chroma_db/` and
reused across requests and restarts.

Embeddings use the Gemini embedding API rather than Chroma's bundled ONNX
model — the ONNX model plus onnxruntime loaded too much memory for a 512MB
hosting instance, so this trades a small amount of API quota for a much
lighter memory footprint.
"""

import json
import os
import re

import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings

from services.gemini_client import get_client

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_CORPUS_DIR = os.path.join(_BASE_DIR, "corpus")
_DEFAULT_DB_PATH = os.path.join(_BASE_DIR, "chroma_db")
_COLLECTION_NAME = "reference_corpus"
_EMBEDDING_MODEL = "gemini-embedding-001"

_CHUNK_SIZE = 500

# Maximum L2 distance for a hit to count as relevant. Calibrated for
# Gemini embeddings: on-topic matches land under 0.5, off-topic above 0.7.
MAX_DISTANCE = 0.6

_collection = None


class GeminiEmbeddingFunction(EmbeddingFunction):
    """Embeds text via the Gemini API instead of a locally loaded model."""

    def __call__(self, input: Documents) -> Embeddings:
        client = get_client()
        response = client.models.embed_content(model=_EMBEDDING_MODEL, contents=input)
        return [e.values for e in response.embeddings]


def _chunk_text(text: str, size: int = _CHUNK_SIZE) -> list[str]:
    """Splits text into chunks of whole sentences."""
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
    """Returns the reference-corpus collection, creating it if needed."""
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=db_path)
        _collection = client.get_or_create_collection(
            name=_COLLECTION_NAME,
            embedding_function=GeminiEmbeddingFunction(),
        )
    return _collection


def _load_sources(corpus_dir: str) -> dict:
    """Loads the corpus metadata sidecar mapping filenames to source details."""
    path = os.path.join(corpus_dir, "sources.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def ingest_corpus(corpus_dir: str = _DEFAULT_CORPUS_DIR, db_path: str = _DEFAULT_DB_PATH) -> int:
    """Embeds every `.txt` document in the corpus into the vector store."""
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
    """Finds the corpus chunks most semantically similar to a query."""
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