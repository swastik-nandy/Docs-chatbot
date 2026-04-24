# --------------------------------------TABLE HANDLER-------------------------------------------

from typing import List, Dict, Any

from rag.ingestion.chunking.engine.builders.chunk_builder import build_chunk


def split(chunk, content: List[Dict[str, Any]]) -> List:
    """
    Handle structured table-like content.

    Strategy:
    - convert each row into a readable key-value string
    - treat each row as atomic knowledge
    - ❌ NO prefix injection here
    - ✅ prefix handled only in chunk_builder
    """

    if not content:
        return [chunk]

    output = []

    for item in content:
        if item.get("type") not in {"table", "generic_table"}:
            continue

        headers = item.get("headers", []) or []
        rows = item.get("rows", []) or []

        for i, row in enumerate(rows):
            if not isinstance(row, dict):
                continue

            parts = []

            for header in headers:
                value = str(row.get(header, "")).strip()
                if not value:
                    continue

                clean_header = str(header).replace("_", " ").strip()
                parts.append(f"{clean_header}: {value}")

            if not parts:
                continue

            row_text = " | ".join(parts)

            output.append(
                build_chunk(
                    original=chunk,
                    text=row_text,
                    subtype="table_row",
                    extra_metadata={
                        "row_index": i,
                        "headers": headers,
                    },
                )
            )

    return output if output else [chunk]