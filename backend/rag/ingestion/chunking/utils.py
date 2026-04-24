# --------------------------------------CHUNKING UTILS-------------------------------------------

import re
from typing import List

import tiktoken


# ---------------- TOKENIZER SETUP ---------------- #

# Initialize once (safe fallback)
try:
    _ENCODING = tiktoken.encoding_for_model("text-embedding-3-small")
except Exception:
    _ENCODING = None


# ---------------- TOKEN ESTIMATION ---------------- #

def estimate_tokens(text: str) -> int:
    """
    Estimate token count safely.

    Strategy:
    - fast approximation for small text
    - accurate encoding when possible
    - fallback-safe
    """

    if not text:
        return 0

    text = text.strip()
    if not text:
        return 0

    # Fast path
    if len(text) < 150:
        return max(1, len(text) // 4)

    if _ENCODING:
        try:
            return len(_ENCODING.encode(text))
        except Exception:
            pass  # fallback below

    return max(1, len(text) // 4)


# ---------------- TEXT NORMALIZATION ---------------- #

def clean_text(text: str) -> str:
    """
    Normalize whitespace while preserving structure.
    """

    if not text:
        return ""

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# ---------------- SAFE JOIN ---------------- #

def join_text(parts: List[str]) -> str:
    """
    Join text parts with semantic separation.
    """

    cleaned = [p.strip() for p in parts if p and p.strip()]
    return "\n\n".join(cleaned) if cleaned else ""


# ---------------- SPLIT BY TOKEN LIMIT ---------------- #

def split_by_token_limit(parts: List[str], max_tokens: int = 600) -> List[str]:
    """
    Group text parts into token-safe chunks.

    Guarantees:
    - preserves order
    - avoids empty chunks
    - tries to keep semantic grouping
    """

    if not parts:
        return []

    chunks: List[str] = []
    buffer: List[str] = []
    buffer_tokens = 0

    for part in parts:
        part = (part or "").strip()
        if not part:
            continue

        tokens = estimate_tokens(part)

        # ---------------- LARGE PART ---------------- #

        if tokens > max_tokens:
            # flush existing buffer first
            if buffer:
                chunks.append(join_text(buffer))
                buffer = []
                buffer_tokens = 0

            # fallback split: paragraph → line
            sub_parts = _safe_split_large(part, max_tokens)
            chunks.extend(sub_parts)
            continue

        # ---------------- NORMAL GROUPING ---------------- #

        if buffer and (buffer_tokens + tokens > max_tokens):
            chunks.append(join_text(buffer))
            buffer = [part]
            buffer_tokens = tokens
        else:
            buffer.append(part)
            buffer_tokens += tokens

    # ---------------- FINAL FLUSH ---------------- #

    if buffer:
        chunks.append(join_text(buffer))

    return chunks


# ---------------- HELPERS ---------------- #

def _safe_split_large(text: str, max_tokens: int) -> List[str]:
    """
    Safely split very large text.

    Strategy:
    1. paragraph split
    2. fallback → line split
    3. last resort → hard cut
    """

    # -------- PARAGRAPH SPLIT -------- #

    parts = [p.strip() for p in text.split("\n\n") if p.strip()]

    if all(estimate_tokens(p) <= max_tokens for p in parts):
        return parts

    # -------- LINE SPLIT -------- #

    parts = [p.strip() for p in text.split("\n") if p.strip()]

    if all(estimate_tokens(p) <= max_tokens for p in parts):
        return parts

    # -------- HARD CUT (LAST RESORT) -------- #

    safe_chunks = []
    approx_size = max_tokens * 4  # rough char-token ratio

    for i in range(0, len(text), approx_size):
        piece = text[i:i + approx_size].strip()
        if piece:
            safe_chunks.append(piece)

    return safe_chunks