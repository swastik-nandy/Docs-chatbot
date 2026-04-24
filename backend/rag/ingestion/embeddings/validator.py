# --------------------------------------EMBEDDING VALIDATOR-------------------------------------------

from typing import List, Tuple
import math

from rag.ingestion.chunking.models import Chunk


# ---------------- CONFIG ---------------- #

MIN_DIM = 10
MAX_DIM = 4096


# ---------------- MAIN ---------------- #

def filter_valid_pairs(
    chunks: List[Chunk],
    embeddings: List[List[float]]
) -> Tuple[List[Chunk], List[List[float]]]:
    """
    Validate embeddings and keep chunk + embedding pairs aligned.

    Rules:
    - strict zip alignment
    - reject malformed vectors
    - reject empty / invalid chunk text
    - enforce consistent embedding dimension
    """

    if not chunks or not embeddings:
        return [], []

    if len(chunks) != len(embeddings):
        raise ValueError(
            f"[EMBED VALIDATOR] Mismatch: {len(chunks)} chunks vs {len(embeddings)} embeddings"
        )

    valid_chunks: List[Chunk] = []
    valid_embeddings: List[List[float]] = []

    expected_dim = _infer_dimension(embeddings)

    if expected_dim == 0:
        raise ValueError("[EMBED VALIDATOR] Could not infer embedding dimension")

    for i, (chunk, vec) in enumerate(zip(chunks, embeddings)):

        if not _is_valid_chunk(chunk):
            continue

        if not _is_valid_vector(vec, expected_dim):
            continue

        valid_chunks.append(chunk)
        valid_embeddings.append(vec)

    return valid_chunks, valid_embeddings


# ---------------- CHUNK VALIDATION ---------------- #

def _is_valid_chunk(chunk: Chunk) -> bool:
    if chunk is None:
        return False

    text = (chunk.text or "").strip()

    # 🔥 reject ultra-small meaningless chunks
    if not text or len(text) < 5:
        return False

    return True


# ---------------- VECTOR VALIDATION ---------------- #

def _is_valid_vector(vec: List[float], expected_dim: int) -> bool:
    if not vec or not isinstance(vec, list):
        return False

    dim = len(vec)

    # strict dimension enforcement
    if dim != expected_dim:
        return False

    if dim < MIN_DIM or dim > MAX_DIM:
        return False

    for x in vec:
        if not isinstance(x, (int, float)):
            return False
        if _is_invalid_number(float(x)):
            return False

    return True


# ---------------- HELPERS ---------------- #

def _is_invalid_number(x: float) -> bool:
    return math.isnan(x) or math.isinf(x)


def _infer_dimension(embeddings: List[List[float]]) -> int:
    """
    Infer expected embedding dimension from the first valid vector.
    """

    for vec in embeddings:
        if isinstance(vec, list) and MIN_DIM <= len(vec) <= MAX_DIM:
            if all(
                isinstance(x, (int, float)) and not _is_invalid_number(float(x))
                for x in vec
            ):
                return len(vec)

    return 0


# ---------------- REPORT ---------------- #

def embedding_validation_report(before_chunks: int, after_chunks: int):
    removed = before_chunks - after_chunks

    print(f"[EMBED VALIDATOR] Before : {before_chunks}")
    print(f"[EMBED VALIDATOR] After  : {after_chunks}")
    print(f"[EMBED VALIDATOR] Removed: {removed}")

    if before_chunks > 0:
        ratio = (removed / before_chunks) * 100
        print(f"[EMBED VALIDATOR] Drop % : {ratio:.2f}%")