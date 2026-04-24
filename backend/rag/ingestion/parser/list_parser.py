#--------------------------------------LIST PARSER-------------------------------------------

from typing import Any


def _clean_item(text: Any) -> str:
    """
    Normalize one list item without adding meaning.
    """
    if text is None:
        return ""

    text = str(text).strip()
    return text


def _has_content(text: str, min_len: int = 2) -> bool:
    return bool(text) and len(text) >= min_len


def _is_ordered_marker(text: str) -> bool:
    """
    Detect common ordered-list style prefixes structurally.
    Examples:
    1. Step
    2) Step
    """
    if not text:
        return False

    text = text.lstrip()
    return (
        len(text) > 2
        and text[0].isdigit()
        and text[1] in {".", ")"}
    )


def _build_generic_block(items: list[str]) -> dict:
    """
    Build a generic list block with minimal structural metadata.
    """
    ordered_votes = sum(1 for item in items if _is_ordered_marker(item))
    is_ordered = ordered_votes >= max(1, len(items) // 2)

    return {
        "type": "list",
        "items": items,
        "ordered": is_ordered,
        "item_count": len(items),
    }


def parse_list(items: list[Any]) -> list[dict]:
    """
    Convert raw list items into generic structural blocks.

    Principles:
    - no domain-specific assumptions
    - preserve order
    - preserve meaning-neutral structure
    - avoid semantic guessing like 'procedure' / 'options'
    """

    cleaned: list[str] = []
    seen: set[str] = set()

    for item in items:
        text = _clean_item(item)

        if not _has_content(text):
            continue

        if text in seen:
            continue

        seen.add(text)
        cleaned.append(text)

    if not cleaned:
        return []

    return [_build_generic_block(cleaned)]