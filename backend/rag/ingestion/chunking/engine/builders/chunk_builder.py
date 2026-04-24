# --------------------------------------CHUNK BUILDER -------------------------------------------

from typing import Dict, Any, Optional, List

from rag.ingestion.chunking.models import Chunk
from rag.ingestion.chunking.utils import estimate_tokens


# ---------------- HELPERS ---------------- #

def _safe_meta(meta: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return dict(meta) if meta else {}


def _normalize_text(text: str) -> str:
    return text.strip() if text else ""


def _build_md_anchor(heading_path: List[str]) -> str:
    return heading_path[-1].strip() if heading_path else ""


def _merge_metadata(
    original_meta: Dict[str, Any],
    subtype: str,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:

    meta = dict(original_meta)

    meta["subtype"] = (subtype or meta.get("subtype") or "text").strip().lower()

    if extra:
        for k, v in extra.items():
            if k != "subtype":
                meta[k] = v

    return meta


# ---------------- MAIN ---------------- #

def build_chunk(
    original: Chunk,
    text: str,
    subtype: str,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> Chunk:

    base_text = _normalize_text(text)
    if not base_text:
        return Chunk(
            text="",
            heading=(original.heading or "").strip(),
            context=(original.context or "").strip(),
            chunk_type=(original.chunk_type or "text"),
            metadata=_safe_meta(original.metadata),
            tokens=0,
            source=(original.source or ""),
        )

    meta = _safe_meta(original.metadata)

    heading_path = meta.get("heading_path") or meta.get("path") or []

    # ---------------- RECOVER HEADING ---------------- #

    heading = (
        (original.heading or "").strip()
        or (meta.get("heading") or "").strip()
        or (heading_path[-1] if heading_path else "")
    )

    context = (
        (original.context or "").strip()
        or (meta.get("context") or "").strip()
        or (heading_path[-2] if len(heading_path) >= 2 else "")
    )

    meta = _merge_metadata(meta, subtype, extra_metadata)

    # store identity in metadata (backup layer)
    meta["heading"] = heading
    meta["context"] = context
    meta["heading_path"] = heading_path

    # ---------------- CLEAN TEXT (NO DUPLICATION) ---------------- #

    anchor = _build_md_anchor(heading_path)

    final_text = base_text

    if anchor:
        # remove accidental heading duplication inside text
        lowered = final_text.lower()
        anchor_lower = anchor.lower()

        if lowered.startswith(anchor_lower):
            final_text = final_text[len(anchor):].strip()

        # add clean anchor once
        final_text = f"{anchor}\n\n{final_text}"

    # ---------------- BUILD ---------------- #

    return Chunk(
        text=final_text,
        heading=heading,
        context=context,
        chunk_type=(original.chunk_type or "text"),
        metadata=meta,
        tokens=estimate_tokens(final_text),
        source=(original.source or meta.get("source", "")),
    )