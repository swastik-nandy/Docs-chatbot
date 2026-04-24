from typing import List, Dict, Any
import os

from google import genai
from google.genai import types


class VectorSearch:

    def __init__(self, store):
        self.store = store

        # ---------------- ENV ---------------- #
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("Missing GEMINI_API_KEY")

        self.model_name = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")

        dim = os.getenv("EMBEDDING_DIMENSION")
        if not dim:
            raise ValueError("Missing EMBEDDING_DIMENSION in .env")

        self.dimension = int(dim)

        # ---------------- CLIENT ---------------- #
        self.client = genai.Client(api_key=self.api_key)

    # ---------------- EMBEDDING ---------------- #

    def _embed_query(self, query: str) -> List[float]:
        """
        MUST match ingestion:
        - same model
        - same dimension
        - task_type = RETRIEVAL_QUERY
        """

        res = self.client.models.embed_content(
            model=self.model_name,
            contents=query,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY",   # 🔥 critical
                output_dimensionality=self.dimension
            )
        )

        vec = res.embeddings[0].values

        if len(vec) != self.dimension:
            raise ValueError(
                f"Embedding dimension mismatch: expected {self.dimension}, got {len(vec)}"
            )

        return list(vec)

    # ---------------- SEARCH ---------------- #

    def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        if not query or not query.strip():
            return []

        query_embedding = self._embed_query(query.strip())

        raw = self.store.query(query_embedding, n_results=top_k)

        payloads = raw.get("payloads") or []
        scores = raw.get("scores") or []

        if not payloads or not scores:
            return []

        max_score = max(scores)
        min_score = min(scores)

        def normalize(s):
            if max_score == min_score:
                return 1.0
            return (s - min_score) / (max_score - min_score)

        results = []

        for payload, score in zip(payloads, scores):
            rtype = (payload.get("type") or "").lower()

            boost = 0.0

            # ---------------- ATOMIC PRIORITY ---------------- #
            if rtype == "flag":
                boost += 0.15
            elif rtype == "command":
                boost += 0.10

            results.append({
                "text": payload.get("text", ""),
                "heading": payload.get("heading", ""),
                "context": payload.get("context", ""),
                "type": payload.get("type", ""),
                "metadata": {
                    "subtype": payload.get("subtype"),
                    "section_type": payload.get("section_type"),
                    "content_role": payload.get("content_role"),
                    "command_context": payload.get("command_context"),
                    "keywords": payload.get("keywords", []),
                    "path": payload.get("path", []),
                    "heading_path": payload.get("heading_path", []),
                    "tokens": payload.get("tokens"),
                    "source": payload.get("source"),
                    "chunk_index": payload.get("chunk_index"),
                    "split_part": payload.get("split_part"),
                },
                "score": float(normalize(score) + boost),
                "source": "vector",
            })

        return results