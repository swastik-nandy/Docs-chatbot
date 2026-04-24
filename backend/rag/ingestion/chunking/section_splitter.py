# --------------------------------------SECTION SPLITTER (DEBUG ENABLED)-------------------------------------------

from typing import List, Dict, Any

from rag.ingestion.chunking.models import Chunk
from rag.ingestion.chunking.utils import clean_text, estimate_tokens


DEBUG = True


def _log(msg: str):
    if DEBUG:
        print(f"[SECTION_SPLITTER] {msg}")


# ---------------- MAIN ---------------- #

def split_sections(
    sections: List[Dict[str, Any]],
    source: str = ""
) -> List[Chunk]:

    if not sections:
        _log("No sections received")
        return []

    chunks: List[Chunk] = []

    _log(f"Total sections received: {len(sections)}")

    for i, section in enumerate(sections):

        _log(f"\n--- SECTION {i} ---")
        _log(f"Keys: {list(section.keys())}")

        # ---------------- HEADING FIX ---------------- #

        heading = (
            section.get("heading")
            or section.get("title")
            or ""
        ).strip()

        heading_path = (
            section.get("heading_path")
            or section.get("path")
            or []
        )

        # fallback from path
        if not heading and heading_path:
            heading = heading_path[-1]
            _log(f"Heading fallback from path: {heading}")

        # context = parent
        context = ""
        if len(heading_path) >= 2:
            context = heading_path[-2]

        if not heading:
            _log("⚠️ WARNING: heading is still empty after fallback")

        _log(f"Heading     : {heading}")
        _log(f"Context     : {context}")
        _log(f"Path        : {heading_path}")

        content = section.get("content", []) or []

        if not content:
            _log("Skipping section (no content)")
            continue

        # ---------------- BLOCKS ---------------- #

        for j, block in enumerate(content):

            if not block:
                continue

            btype = block.get("type")

            _log(f"  Block {j} type: {btype}")

            # -------- PARAGRAPH -------- #

            if btype == "paragraph":
                text = clean_text(block.get("text", ""))

                if not text:
                    continue

                _add_chunk(
                    chunks, text, heading, context,
                    block, section, source,
                    subtype="text", chunk_type="text"
                )

            # -------- LIST -------- #

            elif btype == "list":
                items = block.get("items", []) or []

                for item in items:
                    text = clean_text(str(item))

                    if not text:
                        continue

                    _add_chunk(
                        chunks, text, heading, context,
                        block, section, source,
                        subtype="list_item", chunk_type="list"
                    )

            # -------- TABLE -------- #

            elif btype in {"table", "generic_table"}:
                rows = block.get("rows", [])

                for row in rows:
                    row_text = _format_table_row(row)

                    if not row_text:
                        continue

                    _add_chunk(
                        chunks, row_text, heading, context,
                        block, section, source,
                        subtype="table_row", chunk_type="table"
                    )

            # -------- CODE -------- #

            elif btype == "code":
                code_text = (block.get("text") or "").strip()

                if not code_text:
                    continue

                _add_chunk(
                    chunks, code_text, heading, context,
                    block, section, source,
                    subtype="code_block", chunk_type="code"
                )

            # -------- FALLBACK -------- #

            else:
                fallback = clean_text(block.get("text", ""))

                if not fallback:
                    continue

                _add_chunk(
                    chunks, fallback, heading, context,
                    block, section, source,
                    subtype="text", chunk_type="text"
                )

    _log(f"\nTotal chunks created: {len(chunks)}")

    return chunks


# ---------------- BUILDER ---------------- #

def _add_chunk(
    chunks: List[Chunk],
    text: str,
    heading: str,
    context: str,
    block: Dict[str, Any],
    section: Dict[str, Any],
    source: str,
    subtype: str,
    chunk_type: str,
):
    text = clean_text(text)
    if not text:
        return

    chunk = Chunk(
        text=text,
        heading=heading,
        context=context,
        chunk_type=chunk_type,
        metadata={
            "content": [block],
            "heading_path": section.get("heading_path", []),
            "subtype": subtype,
        },
        tokens=estimate_tokens(text),
        source=source,
    )

    if DEBUG:
        preview = text[:60].replace("\n", " ")
        print(f"    → CHUNK CREATED [{subtype}] | {preview}...")

    chunks.append(chunk)


# ---------------- TABLE FORMATTER ---------------- #

def _format_table_row(row: Any) -> str:

    if isinstance(row, dict):
        values = list(row.values())
    elif isinstance(row, list):
        values = row
    else:
        return ""

    values = [str(v).strip() for v in values if str(v).strip()]

    if not values:
        return ""

    return " | ".join(values)