# --------------------------------------INTENT DETECTOR-------------------------------------------

from typing import List, Dict, Any


def detect_intent(content: List[Dict[str, Any]]) -> str:
    """
    Detect functional intent of content.

    Returns:
        "procedural"
        "descriptive"
        "reference"
        "mixed"
    """

    if not content:
        return "descriptive"

    has_steps = any(item.get("type") == "procedure" for item in content)
    has_table = any(item.get("type") in {"table", "generic_table"} for item in content)
    has_code = any(item.get("type") == "code" for item in content)

    if has_steps:
        return "procedural"

    if has_table:
        return "reference"

    if has_code:
        return "reference"

    return "descriptive"