# --------------------------------------GROUPING UTILS-------------------------------------------

from typing import List

from rag.ingestion.chunking.models import Chunk
from ..builders.chunk_builder import build_chunk
from ...utils import estimate_tokens, join_text


def group_by_tokens(
    chunk: Chunk,
    parts: List[str],
    max_tokens: int,
    subtype: str,
) -> List[Chunk]:
    """
    Adaptive grouping utility.

    Strategy:
    - merge parts into token-safe chunks
    - handle oversized parts safely
    - preserve order
    - avoid empty / weak chunks
    """

    if not parts:
        return [chunk]

    output: List[Chunk] = []
    buffer: List[str] = []
    buffer_tokens = 0

    for part in parts:
        part = (part or "").strip()
        if not part:
            continue

        tokens = estimate_tokens(part)

        # ---------------- HANDLE OVERSIZED PART ---------------- #

        if tokens > max_tokens:
            # flush buffer first
            if buffer:
                output.append(
                    build_chunk(
                        original=chunk,
                        text=join_text(buffer),
                        subtype=subtype,
                    )
                )
                buffer = []
                buffer_tokens = 0

            # split large part safely (paragraph → line fallback)
            split_parts = _safe_split_large(part, max_tokens)

            for sp in split_parts:
                if not sp.strip():
                    continue

                output.append(
                    build_chunk(
                        original=chunk,
                        text=sp.strip(),
                        subtype=subtype,
                    )
                )

            continue

        # ---------------- NORMAL GROUPING ---------------- #

        if buffer and (buffer_tokens + tokens > max_tokens):
            output.append(
                build_chunk(
                    original=chunk,
                    text=join_text(buffer),
                    subtype=subtype,
                )
            )
            buffer = []
            buffer_tokens = 0

        buffer.append(part)
        buffer_tokens += tokens

    # ---------------- FINAL FLUSH ---------------- #

    if buffer:
        output.append(
            build_chunk(
                original=chunk,
                text=join_text(buffer),
                subtype=subtype,
            )
        )

    return output if output else [chunk]


# --------------------------------------HELPERS-------------------------------------------

def _safe_split_large(text: str, max_tokens: int) -> List[str]:
    """
    Safely split very large text blocks.

    Strategy:
    1. paragraph split
    2. fallback → line split
    3. last resort → hard cut
    """

    # -------- PARAGRAPH SPLIT -------- #
    parts = [p.strip() for p in text.split("\n\n") if p.strip()]

    if all(estimate_tokens(p) <= max_tokens for p in parts):
        return parts

    # -------- LINE SPLIT -------- #
    parts = [p.strip() for p in text.split("\n") if p.strip()]

    if all(estimate_tokens(p) <= max_tokens for p in parts):
        return parts

    # -------- HARD CUT -------- #
    safe_chunks = []
    approx_size = max_tokens * 4  # rough char-token ratio

    for i in range(0, len(text), approx_size):
        piece = text[i:i + approx_size].strip()
        if piece:
            safe_chunks.append(piece)

    return safe_chunks