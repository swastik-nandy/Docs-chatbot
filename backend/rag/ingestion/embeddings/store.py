# --------------------------------------QDRANT STORE-------------------------------------------

from typing import List, Dict, Optional, Any

from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    PointStruct,
)

from rag.ingestion.chunking.models import Chunk
from .schema import chunks_to_points


class QdrantStore:
    """
    Handles all interactions with Qdrant DB.
    """

    def __init__(
        self,
        collection_name: str = "docs",
        persist_directory: str = "./qdrant_db",
        vector_size: int = 768,
    ):
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.vector_size = int(vector_size)

        self.client = QdrantClient(path=persist_directory)
        self._ensure_collection(self.vector_size)

    # ---------------- INIT COLLECTION ---------------- #

    def _ensure_collection(self, vector_size: int):
        collections = self.client.get_collections().collections
        names = [c.name for c in collections]

        if self.collection_name not in names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE,
                ),
            )
            return

        info = self.client.get_collection(self.collection_name)
        current_size = info.config.params.vectors.size

        if current_size != vector_size:
            raise ValueError(
                f"Collection '{self.collection_name}' exists with vector size "
                f"{current_size}, expected {vector_size}. "
                "Use a new collection or reset."
            )

    # ---------------- ADD CHUNKS ---------------- #

    def add(
        self,
        chunks: List[Chunk],
        embeddings: List[List[float]],
        batch_size: int = 64,
    ):
        """
        Add chunks + embeddings to Qdrant (batched).
        """

        if not chunks or not embeddings:
            return

        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Mismatch: {len(chunks)} chunks vs {len(embeddings)} embeddings"
            )

        data = chunks_to_points(chunks)

        for start in range(0, len(chunks), batch_size):
            end = start + batch_size

            batch_points: List[PointStruct] = []

            for i in range(start, min(end, len(chunks))):
                vec = embeddings[i]

                if not vec or len(vec) != self.vector_size:
                    continue  # skip invalid (validator already filtered most)

                batch_points.append(
                    PointStruct(
                        id=data["ids"][i],
                        vector=vec,
                        payload=data["payloads"][i],
                    )
                )

            if batch_points:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=batch_points,
                )

    # ---------------- QUERY ---------------- #

    def query(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        filter: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query similar chunks.

        Returns clean structured results.
        """

        if not query_embedding:
            return []

        if len(query_embedding) != self.vector_size:
            raise ValueError(
                f"Query embedding mismatch: got {len(query_embedding)}, expected {self.vector_size}"
            )

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=n_results,
            query_filter=filter,
        )

        return [
            {
                "id": r.id,
                "score": r.score,
                "text": r.payload.get("text"),
                "file_name": r.payload.get("file_name"),
                "heading": r.payload.get("heading"),
                "payload": r.payload,
            }
            for r in results
        ]

    # ---------------- FILTER HELPERS ---------------- #

    def build_file_filter(self, file_name: str) -> Dict:
        """
        Helper to filter by file.
        """
        return {
            "must": [
                {"key": "file_name", "match": {"value": file_name}}
            ]
        }

    # ---------------- RESET ---------------- #

    def reset(self):
        """
        Delete and recreate collection.
        """
        print(f"[QDRANT] Resetting collection: {self.collection_name}")
        self.client.delete_collection(self.collection_name)
        self._ensure_collection(vector_size=self.vector_size)

    # ---------------- COUNT ---------------- #

    def count(self) -> int:
        return self.client.count(self.collection_name).count

    # ---------------- GET ALL ---------------- #

    def get_all(self) -> Dict[str, List]:
        """
        Fetch all payloads (for BM25, debugging, etc.)
        """

        all_points = []
        offset = None

        while True:
            points, offset = self.client.scroll(
                collection_name=self.collection_name,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )

            if not points:
                break

            all_points.extend(points)

            if offset is None:
                break

        return {
            "payloads": [p.payload for p in all_points]
        }