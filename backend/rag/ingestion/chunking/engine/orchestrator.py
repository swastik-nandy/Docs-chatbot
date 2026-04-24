# --------------------------------------ENGINE ORCHESTRATOR (FINAL)-------------------------------------------

from typing import List

from rag.ingestion.chunking.models import Chunk

from rag.ingestion.chunking.engine.detectors.structure import detect_structure
from rag.ingestion.chunking.engine.detectors.intent import detect_intent
from rag.ingestion.chunking.engine.detectors.density import detect_density

from rag.ingestion.chunking.engine.splitters.text import TextSplitter
from rag.ingestion.chunking.engine.splitters.structured import StructuredSplitter
from rag.ingestion.chunking.engine.splitters.procedure import ProcedureSplitter


class EngineOrchestrator:
    """
    Markdown-aware routing engine.

    Rules:
    - Never hard-route lists blindly
    - Let procedure handler inspect lists first
    - Fallback safely to text
    """

    def __init__(self):
        self.text_splitter = TextSplitter()
        self.structured_splitter = StructuredSplitter()
        self.procedure_splitter = ProcedureSplitter()

    # ---------------- MAIN ENTRY ---------------- #

    def process(self, chunks: List[Chunk]) -> List[Chunk]:
        output: List[Chunk] = []

        for chunk in chunks:
            routed = self._route(chunk)
            output.extend(routed)

        return output

    # ---------------- ROUTING ---------------- #

    def _route(self, chunk: Chunk) -> List[Chunk]:
        content = chunk.metadata.get("content", []) or []

        if not content:
            return [chunk]

        structure = detect_structure(content)
        intent = detect_intent(content)
        density = detect_density(content)

        # ---------------- PASS 1: STRONG INTENT ---------------- #

        if intent == "procedural":
            return self.procedure_splitter.split(chunk)

        if intent == "reference":
            return self.structured_splitter.split(chunk)

        # ---------------- PASS 2: TABLE / STRUCTURED ---------------- #

        if structure.get("has_table"):
            return self.structured_splitter.split(chunk)

        # ---------------- PASS 3: LIST → TRY PROCEDURE FIRST ---------------- #
        # 🔥 critical fix: never skip this

        if structure.get("has_list"):
            routed = self.procedure_splitter.split(chunk)

            # if procedure handler actually transformed the chunk
            if routed and routed != [chunk]:
                return routed

        # ---------------- PASS 4: CODE-HEAVY ---------------- #

        if structure.get("has_code") and density == "high":
            return self.structured_splitter.split(chunk)

        # ---------------- PASS 5: TEXT / MIXED ---------------- #

        return self.text_splitter.split(chunk)

    # ---------------- OPTIONAL DEDUPE ---------------- #

    def _dedupe(self, chunks: List[Chunk]) -> List[Chunk]:
        seen = set()
        output = []

        for c in chunks:
            key = (c.text[:200]).strip().lower()
            if key in seen:
                continue
            seen.add(key)
            output.append(c)

        return output