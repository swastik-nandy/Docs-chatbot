# --------------------------------------INGESTION PIPELINE-------------------------------------------

from typing import List

from rag.ingestion.parser import parse
from rag.ingestion.chunking.chunker import chunk_document
from rag.ingestion.chunking.validator import (
    validate_chunks,
    chunk_validation_report,
)

from rag.ingestion.embeddings.embedder import Embedder
from rag.ingestion.embeddings.validator import (
    filter_valid_pairs,
    embedding_validation_report,
)
from rag.ingestion.embeddings.store import QdrantStore


# ---------------- CONFIG ---------------- #

BATCH_SIZE = 32
DEFAULT_COLLECTION_NAME = "docs"
DEFAULT_PERSIST_DIRECTORY = "./qdrant_db"


# ---------------- HELPERS ---------------- #

def _batch(iterable, size=BATCH_SIZE):
    for i in range(0, len(iterable), size):
        yield iterable[i:i + size]


# ---------------- MAIN PIPELINE ---------------- #

def ingest_file(
    file_path: str,
    collection_name: str = DEFAULT_COLLECTION_NAME,
    persist_directory: str = DEFAULT_PERSIST_DIRECTORY,
):
    print("\n[PIPELINE] 🚀 Starting ingestion...")

    # ---------------- PARSE ---------------- #

    documents = parse(file_path)

    if not documents:
        print("[PIPELINE]  No documents parsed")
        return

    doc = documents[0]
    sections = doc.metadata.get("ast", [])

    print(f"[PIPELINE] Sections: {len(sections)}")

    if not sections:
        print("[PIPELINE] ❌ No sections found")
        return

    # ---------------- CHUNKING ---------------- #

    chunks = chunk_document(sections, source=file_path)
    print(f"[PIPELINE] Chunks (raw): {len(chunks)}")

    # ---------------- VALIDATION ---------------- #

    before = len(chunks)
    chunks = validate_chunks(chunks)
    chunk_validation_report(before, len(chunks))

    if not chunks:
        print("[PIPELINE] ❌ No valid chunks")
        return

    # ---------------- INIT ---------------- #

    embedder = Embedder()

    store = QdrantStore(
        collection_name=collection_name,
        persist_directory=persist_directory,
        vector_size=embedder.vector_size,
    )

    print(f"[PIPELINE] Vector size: {embedder.vector_size}")

    # ---------------- PROCESS ---------------- #

    total_before = 0
    total_valid = 0

    for i, batch in enumerate(_batch(chunks)):
        print(f"[PIPELINE] 🔹 Batch {i+1} | size={len(batch)}")

        total_before += len(batch)

        embeddings = embedder.embed_chunks(batch)

        valid_chunks, valid_embeddings = filter_valid_pairs(batch, embeddings)

        if not valid_chunks:
            print(f"[PIPELINE] ⚠️ Batch {i+1} skipped")
            continue

        total_valid += len(valid_chunks)

        store.add(valid_chunks, valid_embeddings)

    # ---------------- REPORT ---------------- #

    embedding_validation_report(total_before, total_valid)

    print(f"[PIPELINE] 📦 Stored chunks: {store.count()}")
    print("[PIPELINE] ✅ Ingestion complete\n")