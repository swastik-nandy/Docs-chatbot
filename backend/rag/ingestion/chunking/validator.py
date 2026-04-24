# --------------------------------------CHUNK VALIDATOR (FINAL)-------------------------------------------

from typing import List, Set, Tuple

from rag.ingestion.chunking.models import Chunk
from rag.ingestion.chunking.engine.detectors.density import detect_density


# ---------------- CONFIG ---------------- #

DEFAULT_MIN_TOKENS = 20        # 🔥 raised
LIGHT_MIN_TOKENS = 10          # for valuable small chunks
MAX_TOKENS = 800

ATOMIC_SUBTYPES = {
    "code_block",
    "table_row",
}

LIGHTWEIGHT_SUBTYPES = {
    "note",
    "fact",
}


# ---------------- MAIN ---------------- #

def validate_chunks(chunks: List[Chunk]) -> List[Chunk]:

    if not chunks:
        return []

    scored: List[Tuple[Chunk, float]] = []
    seen: Set[str] = set()

    for chunk in chunks:
        text = (chunk.text or "").strip()
        if not text:
            continue

        subtype = (chunk.subtype or "").strip().lower()
        content = chunk.metadata.get("content", []) or []

        # ---------------- SIZE POLICY ---------------- #

        min_tokens = _get_min_tokens(subtype)

        if chunk.tokens < min_tokens:
            continue

        if chunk.tokens > MAX_TOKENS:
            continue

        # ---------------- NOISE FILTER ---------------- #

        if _is_noise(text, subtype):
            continue

        # ---------------- DEDUPE ---------------- #

        key = _dedupe_key(text)
        if key in seen:
            continue

        seen.add(key)

        # ---------------- SCORE ---------------- #

        score = _score_chunk(chunk, text, subtype, content)
        scored.append((chunk, score))

    # ---------------- SORT ---------------- #

    scored.sort(key=lambda x: x[1], reverse=True)

    return [_safe_copy(chunk) for chunk, _ in scored]


# ---------------- SCORING ---------------- #

def _score_chunk(chunk: Chunk, text: str, subtype: str, content) -> float:

    score = 0.0

    # -------- LENGTH -------- #

    if 80 <= chunk.tokens <= 400:
        score += 2.0
    elif chunk.tokens > 400:
        score += 1.0
    else:
        score += 0.5

    # -------- SUBTYPE -------- #

    if subtype in ATOMIC_SUBTYPES:
        score += 2.5
    elif subtype == "procedure_group":
        score += 2.0
    elif subtype == "text":
        score += 1.0

    # -------- DENSITY -------- #

    density = detect_density(content)

    if density == "high":
        score += 2.0
    elif density == "medium":
        score += 1.2
    else:
        score += 0.5

    # -------- STRUCTURE -------- #

    if "\n\n" in text:
        score += 0.5

    if ":" in text:
        score += 0.5

    # -------- PENALTY -------- #

    if len(text.split()) < 6:
        score -= 1.5

    return score


# ---------------- TOKEN POLICY ---------------- #

def _get_min_tokens(subtype: str) -> int:

    if subtype in ATOMIC_SUBTYPES:
        return LIGHT_MIN_TOKENS

    if subtype in LIGHTWEIGHT_SUBTYPES:
        return LIGHT_MIN_TOKENS

    return DEFAULT_MIN_TOKENS


# ---------------- NOISE FILTER ---------------- #

def _is_noise(text: str, subtype: str) -> bool:

    lowered = text.lower().strip()

    # allow atomic always
    if subtype in ATOMIC_SUBTYPES | LIGHTWEIGHT_SUBTYPES:
        return False

    # very short → noise
    if len(text.split()) < 5:
        return True

    # repetitive symbols / junk
    if all(not c.isalnum() for c in text):
        return True

    return False


# ---------------- DEDUPE ---------------- #

def _dedupe_key(text: str) -> str:
    return text[:200].lower()


# ---------------- SAFE COPY ---------------- #

def _safe_copy(chunk: Chunk) -> Chunk:
    return Chunk(
        text=chunk.text,
        heading=chunk.heading,
        context=chunk.context,
        chunk_type=chunk.chunk_type,
        subtype=chunk.subtype,
        metadata=dict(chunk.metadata),
        tokens=chunk.tokens,
        source=chunk.source,
        order=chunk.order,
        chunk_id=chunk.chunk_id,
    )