# --------------------------------------LIST HANDLER -------------------------------------------

from typing import List, Dict, Any

from rag.ingestion.chunking.engine.builders.chunk_builder import build_chunk
from rag.ingestion.chunking.utils import estimate_tokens, join_text


# ---------------- CONFIG ---------------- #

# Prefer atomic chunks for short items
ATOMIC_TOKEN_LIMIT = 80

# Group only when items are long
GROUP_SOFT_LIMIT = 180


# ---------------- MAIN ---------------- #

def split(chunk, content: List[Dict[str, Any]]) -> List:
    """
    Markdown-aware list handler.

    Strategy:
    - extract list items
    - normalize & clean
    - classify items by size
    - short items → atomic chunks (high precision)
    - long items → grouped conservatively
    - preserve order
    - no prefix injection (handled by builder)
    """

    if not content:
        return [chunk]

    # ---------------- EXTRACT ---------------- #

    items: List[str] = []

    for item in content:
        if not item:
            continue

        if item.get("type") == "list":
            values = item.get("items", []) or []
            for v in values:
                if not v:
                    continue
                text = str(v).strip()
                if text:
                    items.append(_normalize_item(text))

    if not items:
        return [chunk]

    output: List = []

    # ---------------- ATOMIC FIRST ---------------- #

    long_items: List[str] = []

    for item in items:
        tokens = estimate_tokens(item)

        # short = atomic knowledge
        if tokens <= ATOMIC_TOKEN_LIMIT:
            output.append(
                build_chunk(
                    original=chunk,
                    text=item,
                    subtype="list_item",
                )
            )
        else:
            long_items.append(item)

    # ---------------- GROUP LONG ITEMS ---------------- #

    if long_items:
        buffer: List[str] = []
        buffer_tokens = 0

        for item in long_items:
            t = estimate_tokens(item)

            if buffer and (buffer_tokens + t > GROUP_SOFT_LIMIT):
                output.append(
                    build_chunk(
                        original=chunk,
                        text=join_text(buffer),
                        subtype="list_group",
                    )
                )
                buffer = []
                buffer_tokens = 0

            buffer.append(item)
            buffer_tokens += t

        if buffer:
            output.append(
                build_chunk(
                    original=chunk,
                    text=join_text(buffer),
                    subtype="list_group",
                )
            )

    return output if output else [chunk]


# ---------------- HELPERS ---------------- #

def _normalize_item(text: str) -> str:
    """
    Normalize list item text.

    Goals:
    - remove bullet artifacts
    - preserve semantic content
    - work across messy markdown / CLI docs
    """

    # remove common bullet prefixes

    text = text.lstrip("-*• ").strip()

    # collapse excessive spaces

    text = " ".join(text.split())

    return text