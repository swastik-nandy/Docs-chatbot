from typing import List, Dict, Any
from rank_bm25 import BM25Okapi


class KeywordSearch:
    def __init__(self, chunks: List[Any]):
        self.original_chunks = chunks

        self.valid_chunks = []
        self.texts = []
        self.tokenized = []

        # ---------------- BUILD CORPUS ---------------- #
        for c in chunks:
            text = self._build_search_text(c)

            if not text or not text.strip():
                continue

            tokens = text.lower().split()
            if not tokens:
                continue

            self.valid_chunks.append(c)
            self.texts.append(text)
            self.tokenized.append(tokens)

        if not self.tokenized:
            raise ValueError("BM25 received no valid documents after preprocessing")

        self.bm25 = BM25Okapi(self.tokenized)

    # ---------------- TEXT BUILDER ---------------- #
    def _build_search_text(self, chunk):
        if isinstance(chunk, dict):
            m = chunk.get("metadata", {}) or {}

            parts = [
                chunk.get("heading", ""),
                chunk.get("context", ""),
                m.get("command_context") or "",
                " ".join(m.get("keywords", []) or []),
                chunk.get("text", ""),
            ]
        else:
            m = getattr(chunk, "metadata", {}) or {}

            parts = [
                getattr(chunk, "heading", ""),
                getattr(chunk, "context", ""),
                m.get("command_context") or "",
                " ".join(m.get("keywords", []) or []),
                getattr(chunk, "text", ""),
            ]

        return " ".join(p for p in parts if p).strip()

    # ---------------- SEARCH ---------------- #
    def search(self, query: str, top_k: int = 10) -> List[Dict]:
        if not query or not query.strip():
            return []

        if not self.valid_chunks:
            return []

        tokens = query.lower().split()
        if not tokens:
            return []

        scores = self.bm25.get_scores(tokens)

        if len(scores) == 0:
            return []

        # 🔥 detect intent
        q = query.lower()
        is_command_query = "command" in q or "cli" in q

        ranked = sorted(
            zip(self.valid_chunks, scores),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]

        max_score = float(scores.max())
        min_score = float(scores.min())

        def normalize(s):
            if max_score == min_score:
                return 1.0
            return (s - min_score) / (max_score - min_score)

        results = []

        for c, score in ranked:
            if isinstance(c, dict):
                m = c.get("metadata", {}) or {}
                rtype = (c.get("type", "") or "").lower()
                text = c.get("text", "")
                heading = c.get("heading", "")
                context = c.get("context", "")
            else:
                m = getattr(c, "metadata", {}) or {}
                rtype = (getattr(c, "type", "") or "").lower()
                text = getattr(c, "text", "")
                heading = getattr(c, "heading", "")
                context = getattr(c, "context", "")

            boost = 0.0

            #  QUERY-AWARE BOOSTING
            if is_command_query:
                if rtype == "command":
                    boost += 0.8
                elif rtype == "flag":
                    boost -= 0.3
            else:
                if rtype == "command":
                    boost += 0.4
                elif rtype == "flag":
                    boost += 0.1

            results.append({
                "text": text,
                "heading": heading,
                "context": context,
                "type": rtype,
                "metadata": m,
                "score": float(normalize(score) + boost),
                "source": "bm25",
            })

        return results