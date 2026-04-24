from typing import List, Dict


def format_context(results: List[Dict]) -> str:
    """
    Convert reranked results into structured evidence blocks.
    """

    blocks = []

    for i, r in enumerate(results, 1):
        m = r.get("metadata", {}) or {}

        block = f"""
[Source {i}]
Type: {r.get("type")}
Heading: {r.get("heading")}
Context: {r.get("context")}
Score: {round(r.get("score", 0), 3)}

Content:
{r.get("text")}
"""
        blocks.append(block.strip())

    return "\n\n".join(blocks)