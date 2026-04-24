# --------------------------------------TEXT SPLITTER-------------------------------------------

from typing import List

from rag.ingestion.chunking.models import Chunk
from ..detectors.structure import detect_structure

from ..handlers import text as text_handler
from ..handlers import list as list_handler
from ..handlers import code as code_handler


class TextSplitter:
    """
    Handles general / mixed content.

    Priority:
    1. code
    2. list
    3. text (fallback)
    """

    def split(self, chunk: Chunk) -> List[Chunk]:
        content = chunk.metadata.get("content", []) or []

        if not content:
            return [chunk]

        structure = detect_structure(content)

        # ---------------- CODE PRIORITY ---------------- #

        if structure["has_code"]:
            return code_handler.split(chunk, content)

        # ---------------- LIST HEAVY ---------------- #

        if structure["has_list"] and not structure["has_table"]:
            return list_handler.split(chunk, content)

        # ---------------- DEFAULT TEXT ---------------- #

        return text_handler.split(chunk, content)