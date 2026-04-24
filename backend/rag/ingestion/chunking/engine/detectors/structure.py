# --------------------------------------STRUCTURE DETECTOR-------------------------------------------

from typing import Dict, Any, List


def detect_structure(content: List[Dict[str, Any]]) -> Dict[str, bool]:
    """
    Detect structural signals from content blocks.

    Principles:
    - no domain assumptions
    - only rely on normalized block types
    - fast + predictable
    """

    if not content:
        return _empty_structure()

    has_code = False
    has_table = False
    has_list = False
    has_paragraph = False

    for item in content:
        if not item:
            continue

        t = item.get("type")

        if t == "code":
            has_code = True

        elif t in {"table", "generic_table"}:
            has_table = True

        elif t == "list":
            has_list = True

        elif t == "paragraph":
            has_paragraph = True

        # 🔥 early exit (micro-optimization)
        if has_code and has_table and has_list and has_paragraph:
            break

    return {
        "has_code": has_code,
        "has_table": has_table,
        "has_list": has_list,
        "has_paragraph": has_paragraph,
    }


def _empty_structure() -> Dict[str, bool]:
    return {
        "has_code": False,
        "has_table": False,
        "has_list": False,
        "has_paragraph": False,
    }