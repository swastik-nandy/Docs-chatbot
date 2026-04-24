# --------------------------------------SCHEMA-------------------------------------------

from typing import List, Dict, Any
from rag.ingestion.chunking.models import Chunk
import hashlib
import uuid


# ---------------- SINGLE CONVERSION ---------------- #

def chunk_to_point(chunk: Chunk) -> Dict[str, Any]:
    """
    Convert Chunk -> Qdrant point format.

    Design:
    - keep payload lean but useful
    - optimize for retrieval + filtering
    - preserve traceability
    """

    metadata = chunk.metadata or {}

    # 🔥 derive file name (multi-file UX)
    source = chunk.source or ""
    file_name = source.split("/")[-1] if source else None

    payload = {
        # -------- CORE CONTENT (used in answer generation) -------- #
        "text": chunk.text,
        "heading": chunk.heading,
        "context": chunk.context,

        # -------- SOURCE (multi-file support) -------- #
        "source": source,
        "file_name": file_name,

        # -------- RETRIEVAL SIGNALS -------- #
        "tokens": chunk.tokens,
        "subtype": metadata.get("subtype"),
        "path": metadata.get("path", []),
        "heading_path": metadata.get("heading_path", []),

        # -------- OPTIONAL FILTERING -------- #
        "command_context": metadata.get("command_context"),

        # -------- TRACEABILITY -------- #
        "chunk_index": metadata.get("chunk_index"),
        "split_part": metadata.get("split_part"),
    }

    return {
        "id": _generate_id(chunk),
        "payload": payload,
    }


# ---------------- BULK CONVERSION ---------------- #

def chunks_to_points(chunks: List[Chunk]) -> Dict[str, List]:
    ids = []
    payloads = []

    for chunk in chunks:
        point = chunk_to_point(chunk)
        ids.append(point["id"])
        payloads.append(point["payload"])

    return {
        "ids": ids,
        "payloads": payloads,
    }


# ---------------- ID GENERATION ---------------- #

def _generate_id(chunk: Chunk) -> str:
    """
    Generate stable UUID for Qdrant.

    Deterministic across repeated ingestions of the same chunk content.
    """

    metadata = chunk.metadata or {}

    base = "|".join([
        str(chunk.source or ""),
        str(chunk.heading or ""),
        str(chunk.context or ""),
        str(metadata.get("subtype") or ""),
        str(metadata.get("split_part") or ""),
        str(chunk.text[:200] or ""),
    ])

    hash_bytes = hashlib.sha1(base.encode("utf-8")).digest()[:16]
    return str(uuid.UUID(bytes=hash_bytes))