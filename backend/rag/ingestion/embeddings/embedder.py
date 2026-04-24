# --------------------------------------LOCAL EMBEDDER (BGE BASE GPU-AWARE)-------------------------------------------

import os
from typing import List

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import torch

from rag.ingestion.chunking.models import Chunk


load_dotenv()


class Embedder:
    """
    Production embedder with:
    - BGE-base (768 dim)
    - GPU auto-detection
    - clear device logging
    - retrieval-optimized formatting
    """

    def __init__(self):

        self.model_name = os.getenv("EMBEDDING_MODEL", "BAAI/bge-base-en-v1.5")

        # ---------------- DEVICE DETECTION ---------------- #

        if torch.cuda.is_available():
            self.device = "cuda"
            gpu_name = torch.cuda.get_device_name(0)
            print(f"[EMBEDDER] Using GPU: {gpu_name}")
        else:
            self.device = "cpu"
            print("[EMBEDDER] Using CPU")

        # ---------------- MODEL LOAD ---------------- #

        try:
            self.model = SentenceTransformer(self.model_name, device=self.device)
        except Exception as e:
            raise ValueError(f"[EMBEDDER] Failed to load model '{self.model_name}': {e}")

        # ---------------- DIMENSION ---------------- #

        self._vector_size = self.model.get_sentence_embedding_dimension()

        print(f"[EMBEDDER] Model: {self.model_name}")
        print(f"[EMBEDDER] Dimension: {self._vector_size}")

    # ---------------- PUBLIC ---------------- #

    @property
    def vector_size(self) -> int:
        return self._vector_size

    # ---------------- FORMAT ---------------- #

    def _format_passage(self, chunk: Chunk) -> str:
        metadata = chunk.metadata or {}
        parts: List[str] = []

        if chunk.heading:
            parts.append(chunk.heading.strip())

        if chunk.context and chunk.context != chunk.heading:
            parts.append(chunk.context.strip())

        path = metadata.get("heading_path") or metadata.get("path")
        if path:
            parts.append(" > ".join([str(p).strip() for p in path if p]))

        if chunk.text:
            parts.append(chunk.text.strip())

        return "\n".join(parts)

    # ---------------- EMBED ---------------- #

    def embed_chunks(self, chunks: List[Chunk]) -> List[List[float]]:
        if not chunks:
            return []

        texts = [
            f"passage: {self._format_passage(c)}"
            for c in chunks
        ]

        embeddings = self.model.encode(
            texts,
            batch_size=64,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        return embeddings.tolist()

    def embed_query(self, query: str) -> List[float]:
        if not query:
            return []

        vec = self.model.encode(
            [f"query: {query.strip()}"],
            normalize_embeddings=True,
        )

        return vec[0].tolist()