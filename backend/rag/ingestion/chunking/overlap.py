# --------------------------------------OVERLAP-------------------------------------------

from typing import List
import re

from rag.ingestion.chunking.models import Chunk
from rag.ingestion.chunking.engine.builders.chunk_builder import build_chunk
from rag.ingestion.chunking.engine.detectors.density import detect_density


# ---------------- CONFIG ---------------- #

BASE_OVERLAP_CHARS = 200

ATOMIC_SUBTYPES = {
    "code_block",
    "table_row",
}

# NEW: small chunks shouldn't get overlap
MIN_TOKENS_FOR_OVERLAP = 80


# ---------------- MAIN ---------------- #

def apply_overlap(chunks: List[Chunk]) -> List[Chunk]:
    """
    Adaptive overlap injection.

    Strategy:
    - skip atomic chunks
    - skip small chunks
    - adapt overlap size based on density + subtype
    - extract meaningful trailing context
    - inject using builder (consistent pipeline)
    """

    if not chunks:
        return []

    output = [chunks[0]]

    for i in range(1, len(chunks)):
        prev = output[-1]
        curr = chunks[i]

        prev_subtype = (prev.metadata.get("subtype") or "").strip().lower()
        curr_subtype = (curr.metadata.get("subtype") or "").strip().lower()

        # ---------------- SKIP ATOMIC ---------------- #

        if prev_subtype in ATOMIC_SUBTYPES or curr_subtype in ATOMIC_SUBTYPES:
            output.append(curr)
            continue

        # ---------------- SKIP SMALL CHUNKS ---------------- #

        if curr.tokens < MIN_TOKENS_FOR_OVERLAP:
            output.append(curr)
            continue

        # ---------------- ADAPTIVE SIZE ---------------- #

        overlap_chars = _get_overlap_size(prev)

        # ---------------- EXTRACT ---------------- #

        overlap = _extract_overlap(prev.text, overlap_chars)

        # ---------------- APPLY ---------------- #

        if overlap and not _already_has_overlap(curr.text, overlap):
            new_text = f"{overlap}\n\n{curr.text}".strip()

            output.append(
                build_chunk(
                    original=curr,
                    text=new_text,
                    subtype=curr.metadata.get("subtype", "overlap"),
                    extra_metadata={"overlap": True},
                )
            )
        else:
            output.append(curr)

    return output


# ---------------- ADAPTIVE SIZE ---------------- #

def _get_overlap_size(chunk: Chunk) -> int:
    """
    Adjust overlap size based on density + subtype.
    """

    subtype = (chunk.metadata.get("subtype") or "").lower()
    content = chunk.metadata.get("content", []) or []

    # subtype-based tuning (slightly reduced)
    if subtype == "text":
        return 180

    if subtype == "list":
        return 100

    if subtype == "procedure":
        return 80

    # density-based tuning
    density = detect_density(content)

    if density == "high":
        return 80

    if density == "medium":
        return 120

    return BASE_OVERLAP_CHARS


# ---------------- EXTRACT ---------------- #

def _extract_overlap(text: str, max_chars: int) -> str:
    """
    Extract meaningful trailing context.
    """

    if not text:
        return ""

    parts = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not parts:
        return ""

    last_block = parts[-1]

    sentences = _split_sentences(last_block)

    overlap = " ".join(sentences[-2:]) if len(sentences) >= 2 else last_block
    overlap = overlap.strip()

    # ---------------- FILTER ---------------- #

    if len(overlap.split()) < 6:
        return ""

    if overlap.endswith(":"):
        return ""

    if not overlap.endswith("."):
        overlap += "."

    if len(overlap) > max_chars:
        overlap = overlap[-max_chars:]

    lowered = overlap.lower()

    if lowered.startswith("root"):
        return ""

    if "last updated" in lowered:
        return ""

    return overlap


# ---------------- HELPERS ---------------- #

def _split_sentences(text: str) -> List[str]:
    return [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+", text)
        if s.strip()
    ]


def _already_has_overlap(text: str, overlap: str) -> bool:
    """
    Stronger guard against near-duplicates.
    """
    window = text[:len(overlap) + 20].lower()
    return overlap.lower() in window