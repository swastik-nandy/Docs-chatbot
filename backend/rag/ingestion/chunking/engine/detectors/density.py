# --------------------------------------DENSITY DETECTOR-------------------------------------------

from typing import List, Dict, Any


def detect_density(content: List[Dict[str, Any]]) -> str:
    """
    Classify chunk density.

    Returns:
        "low"     → mostly paragraphs
        "medium"  → mix of lists / paragraphs
        "high"    → code / structured / dense content
    """

    if not content:
        return "low"

    score = 0

    for item in content:
        itype = item.get("type")

        if itype == "code":
            score += 3

        elif itype in {"table", "generic_table"}:
            score += 3

        elif itype in {"list", "bullets", "options", "navigation"}:
            score += 2

        elif itype == "procedure":
            score += 2

        elif itype == "paragraph":
            score += 1

    avg_score = score / max(len(content), 1)

    if avg_score >= 2.2:
        return "high"

    if avg_score >= 1.4:
        return "medium"

    return "low"