# --------------------------------------TEXT HANDLER-------------------------------------------

from typing import List, Dict, Any
import re

from rag.ingestion.chunking.engine.builders.chunk_builder import build_chunk
from rag.ingestion.chunking.utils import estimate_tokens


ATOMIC_LIMIT = 120
MAX_BLOCK = 300


def split(chunk, content: List[Dict[str, Any]]) -> List:
    """
    Handle narrative / fallback content.

    Strategy:
    - extract paragraph-level text
    - keep small paragraphs atomic
    - split large paragraphs safely
    - avoid blind grouping
    """

    if not content:
        return [chunk]

    parts: List[str] = []

    # ---------------- EXTRACT ---------------- #

    for item in content:
        if not item:
            continue

        t = item.get("type")

        if t == "paragraph":
            text = (item.get("text") or "").strip()
            if text:
                parts.append(_normalize(text))
            continue

        if "text" in item:
            text = (item.get("text") or "").strip()
            if text:
                parts.append(_normalize(text))

    if not parts:
        return [chunk]

    output = []

    # ---------------- PROCESS ---------------- #

    for part in parts:
        tokens = estimate_tokens(part)

        # small → atomic
        if tokens <= ATOMIC_LIMIT:
            output.append(
                build_chunk(
                    original=chunk,
                    text=part,
                    subtype="text_atom",
                )
            )
            continue

        # medium → keep as is
        if tokens <= MAX_BLOCK:
            output.append(
                build_chunk(
                    original=chunk,
                    text=part,
                    subtype="text_block",
                )
            )
            continue

        # large → split
        for piece in _split_large(part):
            if not piece:
                continue

            output.append(
                build_chunk(
                    original=chunk,
                    text=piece,
                    subtype="text_split",
                )
            )

    return output if output else [chunk]


# ---------------- HELPERS ---------------- #

def _normalize(text: str) -> str:
    return " ".join(text.split()).strip()


def _split_large(text: str) -> List[str]:
    """
    Split large text into sentence groups.
    """

    sentences = [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+", text)
        if s.strip()
    ]

    chunks = []
    buffer = []
    tokens = 0

    for s in sentences:
        t = estimate_tokens(s)

        if buffer and tokens + t > MAX_BLOCK:
            chunks.append(" ".join(buffer))
            buffer = []
            tokens = 0

        buffer.append(s)
        tokens += t

    if buffer:
        chunks.append(" ".join(buffer))

    return chunks