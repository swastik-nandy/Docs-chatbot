# --------------------------------------CODE HANDLER-------------------------------------------

from typing import List, Dict, Any

from rag.ingestion.chunking.engine.builders.chunk_builder import build_chunk


def split(chunk, content: List[Dict[str, Any]]) -> List:
    """
    Handle code-like content.

    Strategy:
    - isolate each code block
    - do NOT group or split code
    - ❌ NO prefix injection here
    - ✅ prefix handled only in chunk_builder
    """

    if not content:
        return [chunk]

    output = []

    for item in content:
        if item.get("type") != "code":
            continue

        code = (item.get("text") or "").strip()
        if not code:
            continue

        output.append(
            build_chunk(
                original=chunk,
                text=code,
                subtype="code_block",
            )
        )

    return output if output else [chunk]