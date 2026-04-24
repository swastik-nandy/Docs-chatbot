# --------------------------------------EMBED DEBUG PIPELINE-------------------------------------------

from pathlib import Path
from collections import Counter
from statistics import mean, median

from rag.ingestion.parser import parse
from rag.ingestion.chunking.chunker import chunk_document
from rag.ingestion.chunking.validator import validate_chunks

from rag.ingestion.embeddings.embedder import Embedder
from rag.ingestion.embeddings.validator import filter_valid_pairs
from rag.ingestion.embeddings.store import QdrantStore


# ---------------- UI HELPERS ---------------- #

def _divider(title: str):
    print("\n" + "=" * 90)
    print(title)
    print("=" * 90)


def _subdivider(title: str):
    print("\n" + "-" * 60)
    print(title)
    print("-" * 60)


def _preview(text: str, limit: int = 160) -> str:
    text = (text or "").strip().replace("\n", " ")
    return text[:limit] + ("..." if len(text) > limit else "")


def _resolve_path(file_path: str) -> str:
    p = Path(file_path)
    if p.exists():
        return str(p.resolve())

    root = Path(__file__).resolve().parent.parent
    candidate = root / file_path
    if candidate.exists():
        return str(candidate.resolve())

    raise FileNotFoundError(file_path)


# ---------------- ANALYTICS ---------------- #

def _token_stats(chunks):
    tokens = [c.tokens for c in chunks]
    return {
        "avg": int(mean(tokens)),
        "median": int(median(tokens)),
        "min": min(tokens),
        "max": max(tokens),
    }


# ---------------- CORE ---------------- #

def run_embed_debug(file_path: str):

    _divider("🚀 EMBEDDING DEBUG PIPELINE")

    path = _resolve_path(file_path)
    print(f"[INFO] File: {path}")

    # ---------------- PARSE ---------------- #

    docs = parse(path)
    if not docs:
        print("❌ Parse failed")
        return

    doc = docs[0]
    sections = (doc.metadata or {}).get("ast", [])

    print(f"[INFO] Sections: {len(sections)}")

    # ---------------- CHUNK ---------------- #

    chunks = chunk_document(sections, source=path)

    print(f"[INFO] Raw chunks: {len(chunks)}")

    chunks = validate_chunks(chunks)
    print(f"[INFO] Valid chunks: {len(chunks)}")

    if not chunks:
        print("❌ No valid chunks")
        return

    # ---------------- STATS ---------------- #

    stats = _token_stats(chunks)

    subtype_counts = Counter(
        (c.metadata.get("subtype") or "unknown")
        for c in chunks
    )

    _divider("📊 CHUNK STATS")

    print(f"[INFO] Subtypes: {dict(subtype_counts)}")
    print(
        f"[INFO] Tokens → avg: {stats['avg']} | "
        f"median: {stats['median']} | min: {stats['min']} | max: {stats['max']}"
    )

    # ---------------- EMBEDDING ---------------- #

    embedder = Embedder()

    _divider("🧠 EMBEDDING")

    embeddings = embedder.embed_chunks(chunks)

    valid_chunks, valid_embeddings = filter_valid_pairs(chunks, embeddings)

    print(f"[INFO] Valid embeddings: {len(valid_embeddings)}")

    if not valid_embeddings:
        print("❌ No valid embeddings")
        return

    # ---------------- STORE ---------------- #

    _divider("📦 QDRANT STORE")

    collection_name = f"debug_{Path(path).stem}"

    store = QdrantStore(
        collection_name=collection_name,
        vector_size=embedder.vector_size,
    )

    store.reset()  # always fresh run

    store.add(valid_chunks, valid_embeddings)

    print(f"[INFO] Stored chunks: {store.count()}")

    # ---------------- SAMPLE QUERY ---------------- #

    _divider("🔍 SAMPLE QUERY")

    sample_query = "what are the available commands"
    print(f"[QUERY] {sample_query}")

    query_vec = embedder.embed_query(sample_query)

    results = store.query(query_vec, n_results=5)

    if not results:
        print("❌ No results returned")
        return

    for r in results:
        _subdivider("RESULT")
        print(f"Score    : {round(r['score'], 4)}")
        print(f"File     : {r.get('file_name')}")
        print(f"Heading  : {r.get('heading')}")
        print(f"Preview  : {_preview(r.get('text'))}")

    print("\n✅ EMBEDDING PIPELINE COMPLETE")


# ---------------- ENTRY ---------------- #

def main():
    print("⚡ EMBED DEBUG MODE\n")
    run_embed_debug("docs/next_js.md")


if __name__ == "__main__":
    main()