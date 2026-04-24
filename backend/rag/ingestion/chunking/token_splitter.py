# --------------------------------------TOKEN SPLITTER-------------------------------------------

from typing import List
import re

from rag.ingestion.chunking.models import Chunk
from rag.ingestion.chunking.utils import estimate_tokens
from rag.ingestion.chunking.engine.builders.chunk_builder import build_chunk
from rag.ingestion.chunking.engine.detectors.density import detect_density


# ---------------- CONFIG ---------------- #

DEFAULT_MAX_TOKENS = 600

# do not split these (CRITICAL)
ATOMIC_SUBTYPES = {
    "code_block",
    "table_row",
    "list_item",
    "text_atom",
    "procedure_step",   # 🔥 added
}


# ---------------- MAIN ---------------- #

def enforce_token_limit(
    chunks: List[Chunk],
    max_tokens: int = DEFAULT_MAX_TOKENS
) -> List[Chunk]:

    if not chunks:
        return []

    output: List[Chunk] = []

    for chunk in chunks:
        subtype = (chunk.metadata.get("subtype") or "").strip().lower()
        content = chunk.metadata.get("content", []) or []

        # -------- ATOMIC -------- #
        if subtype in ATOMIC_SUBTYPES:
            output.append(chunk)
            continue

        # -------- ADAPTIVE LIMIT -------- #
        adaptive_limit = _get_adaptive_limit(
            base=max_tokens,
            subtype=subtype,
            content=content,
        )

        # -------- SAFE -------- #
        if chunk.tokens <= adaptive_limit:
            output.append(chunk)
            continue

        # -------- SPLIT -------- #
        output.extend(_split_large_chunk(chunk, adaptive_limit))

    return output


# ---------------- ADAPTIVE LIMIT ---------------- #

def _get_adaptive_limit(base: int, subtype: str, content) -> int:

    if subtype == "code_block":
        return min(base, 300)

    if subtype == "table_row":
        return min(base, 200)

    if subtype == "list_group":
        return min(base, 400)

    if subtype == "text_block":
        return min(base, 500)

    density = detect_density(content)

    if density == "high":
        return min(base, 400)

    if density == "medium":
        return min(base, 550)

    return base


# ---------------- SPLIT LOGIC ---------------- #

def _split_large_chunk(chunk: Chunk, max_tokens: int) -> List[Chunk]:

    text = (chunk.text or "").strip()
    if not text:
        return []

    # -------- STEP 1: PARAGRAPH SPLIT -------- #

    parts = [p.strip() for p in text.split("\n\n") if p.strip()]

    # -------- STEP 2: SENTENCE SPLIT -------- #

    sentence_mode = False

    if len(parts) == 1:
        parts = _split_by_sentences(text)
        sentence_mode = True

    # -------- GROUPING STRATEGY -------- #

    if sentence_mode:
        # 🔥 do NOT aggressively group sentences
        grouped = _group_sentences_safely(parts, max_tokens)
    else:
        grouped = _group_by_tokens(parts, max_tokens)

    # -------- FALLBACK: LINE SPLIT -------- #

    if any(estimate_tokens(p) > max_tokens for p in grouped):
        parts = [p.strip() for p in text.split("\n") if p.strip()]
        grouped = _group_by_tokens(parts, max_tokens)

    # -------- BUILD -------- #

    new_chunks: List[Chunk] = []

    for i, part in enumerate(grouped):
        if not part:
            continue

        new_chunks.append(
            build_chunk(
                original=chunk,
                text=part,
                subtype=chunk.metadata.get("subtype", "text_split"),
                extra_metadata={"split_part": i},
            )
        )

    return new_chunks


# ---------------- HELPERS ---------------- #

def _split_by_sentences(text: str) -> List[str]:
    parts = [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+", text)
        if s.strip()
    ]
    return parts if parts else [text]


def _group_sentences_safely(parts: List[str], max_tokens: int) -> List[str]:
    """
    Prefer atomic sentences unless they exceed limits.
    """

    output = []

    for part in parts:
        if estimate_tokens(part) <= max_tokens:
            output.append(part)
        else:
            # fallback to token grouping if a single sentence is too large
            output.extend(_group_by_tokens([part], max_tokens))

    return output


def _group_by_tokens(parts: List[str], max_tokens: int) -> List[str]:
    buffer = []
    tokens = 0
    output = []

    for part in parts:
        t = estimate_tokens(part)

        if buffer and tokens + t > max_tokens:
            output.append(" ".join(buffer))
            buffer = []
            tokens = 0

        buffer.append(part)
        tokens += t

    if buffer:
        output.append(" ".join(buffer))

    return output