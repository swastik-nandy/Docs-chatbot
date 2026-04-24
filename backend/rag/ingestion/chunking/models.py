from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import hashlib


@dataclass
class Chunk:
    # ---------------- CORE ---------------- #
    text: str
    chunk_type: str  # e.g., "text", "list", "code", "table"

    # ---------------- CONTEXT ---------------- #
    heading: str = ""
    context: str = ""

    # ---------------- STRUCTURE ---------------- #
    subtype: str = ""   # explicit (no more metadata-only access)
    order: int = 0      # preserves document flow

    # ---------------- METADATA ---------------- #
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ---------------- STATS ---------------- #
    tokens: int = 0
    source: str = ""

    # ---------------- INTERNAL ---------------- #
    chunk_id: Optional[str] = None


    # ---------------- INIT ---------------- #

    def __post_init__(self):
        # normalize text fields
        self.text = (self.text or "").strip()
        self.heading = (self.heading or "").strip()
        self.context = (self.context or "").strip()

        # normalize subtype
        self.subtype = (
            (self.subtype or "").strip().lower()
            or (self.metadata.get("subtype") or "").strip().lower()
        )

        # ensure metadata carries identity (backup layer)
        if self.heading:
            self.metadata.setdefault("heading", self.heading)
        if self.context:
            self.metadata.setdefault("context", self.context)
        if self.subtype:
            self.metadata.setdefault("subtype", self.subtype)

        # generate stable id if missing
        if not self.chunk_id:
            self.chunk_id = self._generate_id()


    # ---------------- ID ---------------- #

    def _generate_id(self) -> str:
        """
        Stable identity for:
        - dedupe
        - caching
        - debugging

        Uses stable components only.
        """
        base = f"{self.source}|{self.heading}|{self.context}|{self.text[:120]}"
        return hashlib.md5(base.encode("utf-8")).hexdigest()


    # ---------------- SERIALIZATION ---------------- #

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.chunk_id,
            "text": self.text,
            "heading": self.heading,
            "context": self.context,
            "type": self.chunk_type,
            "subtype": self.subtype,
            "order": self.order,
            "tokens": self.tokens,
            "source": self.source,
            "metadata": self.metadata,
        }


    # ---------------- DEBUG ---------------- #

    def __repr__(self) -> str:
        preview = self.text.replace("\n", " ")[:50]
        return (
            f"<Chunk id={self.chunk_id[:8]} "
            f"type={self.chunk_type}/{self.subtype} "
            f"tokens={self.tokens} "
            f"text='{preview}...'>"
        )