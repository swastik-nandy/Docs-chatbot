# --------------------------------------PROCEDURE SPLITTER-------------------------------------------

from typing import List

from rag.ingestion.chunking.models import Chunk
from rag.ingestion.chunking.engine.handlers import procedure as procedure_handler


class ProcedureSplitter:
    """
    Dedicated splitter for procedural content.
    """

    def split(self, chunk: Chunk) -> List[Chunk]:
        content = chunk.metadata.get("content", []) or []

        return procedure_handler.split(chunk, content)