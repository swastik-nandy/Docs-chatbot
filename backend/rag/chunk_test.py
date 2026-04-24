# --------------------------------------CHUNK DEBUG PIPELINE (FINAL)-------------------------------------------

from pathlib import Path
from collections import Counter
from statistics import mean, median

from rag.ingestion.parser import parse
from rag.ingestion.chunking.chunker import chunk_document


# ---------------- CONFIG ---------------- #

MAX_CHUNKS_DISPLAY = 12   # limit per file to avoid noise


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


def _resolve_path(file_path: str) -> Path:
    p = Path(file_path)

    if p.exists():
        return p.resolve()

    root = Path(__file__).resolve().parent.parent
    candidate = root / file_path

    if candidate.exists():
        return candidate.resolve()

    raise FileNotFoundError(file_path)


# ---------------- ANALYTICS ---------------- #

def _token_stats(chunks):
    tokens = [c.tokens for c in chunks] or [0]
    return {
        "avg": int(mean(tokens)),
        "median": int(median(tokens)),
        "min": min(tokens),
        "max": max(tokens),
    }


# ---------------- CORE ---------------- #

def run_chunk_debug(file_path: str):

    path = _resolve_path(file_path)

    _divider(f"📄 FILE → {path}")

    # ---------------- PARSE ---------------- #

    docs = parse(str(path))
    if not docs:
        print("❌ Parse failed")
        return

    doc = docs[0]
    sections = (doc.metadata or {}).get("ast", [])

    print(f"[INFO] Sections: {len(sections)}")

    # ---------------- CHUNK ---------------- #

    chunks = chunk_document(sections, source=str(path))

    print(f"[INFO] Final chunks: {len(chunks)}")

    if not chunks:
        print("❌ No chunks produced")
        return

    # ---------------- STATS ---------------- #

    stats = _token_stats(chunks)

    subtype_counter = Counter(
        (c.subtype or c.metadata.get("subtype") or "unknown")
        for c in chunks
    )

    print(f"[INFO] Subtypes: {dict(subtype_counter)}")
    print(f"[INFO] Tokens → avg: {stats['avg']} | min: {stats['min']} | max: {stats['max']}")

    # ---------------- DISPLAY ---------------- #

    for i, c in enumerate(chunks[:MAX_CHUNKS_DISPLAY]):

        _subdivider(f"CHUNK {i}")

        print(f"Subtype  : {c.subtype}")
        print(f"Tokens   : {c.tokens}")
        print(f"Heading  : {c.heading}")
        print(f"Context  : {c.context}")
        print(f"Source   : {c.source}")
        print(f"Preview  : {_preview(c.text)}")

    if len(chunks) > MAX_CHUNKS_DISPLAY:
        print(f"\n... ({len(chunks) - MAX_CHUNKS_DISPLAY} more chunks hidden)")

    print("\n✅ FILE COMPLETE")


# ---------------- FOLDER MODE ---------------- #

def run_folder_debug(folder_path: str):

    base_path = _resolve_path(folder_path)

    _divider(f"📁 FOLDER → {base_path}")

    md_files = list(base_path.rglob("*.md"))

    if not md_files:
        print("❌ No markdown files found")
        return

    print(f"[INFO] Found {len(md_files)} markdown files\n")

    for i, file in enumerate(md_files, start=1):

        print("\n" + "#" * 100)
        print(f"[{i}/{len(md_files)}] PROCESSING → {file}")
        print("#" * 100)

        try:
            run_chunk_debug(str(file))
        except Exception as e:
            print(f"❌ ERROR processing {file}: {e}")


# ---------------- ENTRY ---------------- #

def main():
    print("⚡ CHUNK DEBUG MODE (CORPUS TEST)\n")

    # 🔥 switch between modes here:

    # --- single file ---
    # run_chunk_debug("docs/mellisearch/agents.md")

    # --- folder mode ---
    run_folder_debug("docs/mellisearch/claude/commands")


if __name__ == "__main__":
    main()