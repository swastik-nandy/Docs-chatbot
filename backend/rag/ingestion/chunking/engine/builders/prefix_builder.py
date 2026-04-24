# --------------------------------------PREFIX BUILDER-------------------------------------------

from rag.ingestion.chunking.models import Chunk


def build_prefix(chunk: Chunk) -> str:
    """
    Generate stable identity prefix.

    Keeps chunk grounded in context without duplication.
    """

    context = (chunk.context or "").strip()
    heading = (chunk.heading or "").strip()

    if context and heading:
        # 🔥 avoid redundant prefix like "Reference - Reference"
        if heading.lower() in context.lower():
            return context
        return f"{context} - {heading}"

    return context or heading or ""