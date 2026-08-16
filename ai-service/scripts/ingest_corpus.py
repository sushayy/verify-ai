"""Embeds the reference corpus into ChromaDB.

The service also does this at startup, so this script is for rebuilding the
store by hand after editing `corpus/` — useful when adding reference documents
without restarting the API.

Run from the `ai-service/` directory:

    python scripts/ingest_corpus.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import vector_store  # noqa: E402


def main() -> None:
    """Ingests the corpus and reports how many chunks are indexed."""
    count = vector_store.ingest_corpus()
    total = vector_store.get_collection().count()
    print(f"Ingested {count} chunks. Collection now holds {total}.")


if __name__ == "__main__":
    main()
