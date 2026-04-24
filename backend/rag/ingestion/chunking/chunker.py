# --------------------------------------CHUNKER (FINAL PIPELINE)-------------------------------------------

from typing import List

from .models import Chunk
from .section_splitter import split_sections
from .token_splitter import enforce_token_limit
from .validator import validate_chunks

from .engine.orchestrator import EngineOrchestrator


# ---------------- CONFIG ---------------- #

DEFAULT_MAX_TOKENS = 600
ENABLE_OVERLAP = False  # 🔥 disabled by default (atomic-first design)


# ---------------- MAIN ---------------- #

def chunk_document(
    sections,
    source: str = "",
    max_tokens: int = DEFAULT_MAX_TOKENS,
    enable_overlap: bool = ENABLE_OVERLAP
) -> List[Chunk]:
    """
    Production chunking pipeline.

    Order (STRICT):
        1. Section → base chunks (structure extraction)
        2. Engine → structure-aware splitting
        3. Token enforcement → size safety
        4. Validation → quality filtering

    Notes:
        - Overlap disabled by default (harms atomic precision)
        - No text mutation outside handlers/builders
        - Fully deterministic flow
    """

    if not sections:
        return []

    # ---------------- STEP 1: SECTION SPLIT ---------------- #

    base_chunks = split_sections(sections, source=source)

    if not base_chunks:
        return []

    # ---------------- STEP 2: ENGINE ---------------- #

    engine = EngineOrchestrator()
    processed_chunks = engine.process(base_chunks)

    if not processed_chunks:
        return []

    # ---------------- STEP 3: TOKEN ENFORCEMENT ---------------- #

    token_safe_chunks = enforce_token_limit(
        processed_chunks,
        max_tokens=max_tokens
    )

    if not token_safe_chunks:
        return []

    # ---------------- STEP 4: VALIDATION ---------------- #

    final_chunks = validate_chunks(token_safe_chunks)

    if not final_chunks:
        return []

    # ---------------- OPTIONAL: OVERLAP (EXPLICIT ONLY) ---------------- #

    if enable_overlap:
        from .overlap import apply_overlap
        final_chunks = apply_overlap(final_chunks)

    return final_chunks