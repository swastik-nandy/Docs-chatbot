# --------------------------------------LIST ENRICHER-------------------------------------------

from typing import List, Dict, Any


def _clean_items(items: List[Any], min_len: int = 1) -> List[str]:
    """
    Normalize list items while preserving meaning.
    """
    cleaned = []

    for item in items or []:
        text = str(item).strip()
        if text and len(text) >= min_len:
            cleaned.append(text)

    return cleaned


def _detect_ordered(items: List[str]) -> bool:
    """
    Generic ordered list detection (structure-only).
    """
    if not items:
        return False

    hits = 0

    for item in items:
        item = item.lstrip()
        if len(item) > 2 and item[0].isdigit() and item[1] in {".", ")"}:
            hits += 1

    return hits >= max(1, len(items) // 2)


def enrich_lists(content: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert list_block → list

    Principles:
    - NEVER drop valid list signal
    - no domain assumptions
    - minimal transformation
    """

    new_content: List[Dict[str, Any]] = []

    for item in content:
        if not item:
            continue

        t = item.get("type")

        # ---------------- LIST BLOCK ---------------- #

        if t == "list_block":
            raw_items = item.get("items", []) or []
            items = _clean_items(raw_items)

            # 🔥 critical: do NOT silently drop list blocks
            if not items:
                # preserve structure even if items are weak
                new_content.append({
                    "type": "list",
                    "items": [],
                    "ordered": False,
                })
                continue

            new_content.append({
                "type": "list",
                "items": items,
                "ordered": _detect_ordered(items),
            })
            continue

        # ---------------- LEGACY SUPPORT ---------------- #

        if t == "list_raw":
            raw_items = item.get("items", []) or []
            items = _clean_items(raw_items)

            if items:
                new_content.append({
                    "type": "list",
                    "items": items,
                    "ordered": _detect_ordered(items),
                })
            else:
                new_content.append({
                    "type": "list",
                    "items": [],
                    "ordered": False,
                })
            continue

        # ---------------- PASS THROUGH ---------------- #

        new_content.append(item)

    return new_content