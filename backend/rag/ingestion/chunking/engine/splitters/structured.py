# --------------------------------------STRUCTURED SPLITTER-------------------------------------------

from typing import List

from rag.ingestion.chunking.models import Chunk
from rag.ingestion.chunking.engine.detectors.structure import detect_structure

from rag.ingestion.chunking.engine.handlers import table as table_handler
from rag.ingestion.chunking.engine.handlers import text as text_handler


class StructuredSplitter:
    """
    Handles structured content (tables + supporting text).
    """

    def split(self, chunk: Chunk) -> List[Chunk]:
        content = chunk.metadata.get("content", []) or []

        if not content:
            return [chunk]

        structure = detect_structure(content)

        # ---------------- TABLE HANDLING ---------------- #

        if structure["has_table"]:
            table_chunks = table_handler.split(chunk, content)

            # include supporting narrative text
            text_chunks = text_handler.split(chunk, content)

            return table_chunks + text_chunks if text_chunks else table_chunks

        return [chunk]