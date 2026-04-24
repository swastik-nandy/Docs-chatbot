# --------------------------------------TEXT ENRICHER-------------------------------------------

import re
from typing import List, Dict, Any


# ---------------- CLEAN TEXT ---------------- #

def _clean_text(text: str) -> str:
    """
    Normalize inline markdown without destroying meaning.
    """
    if not text:
        return ""

    text = str(text)

    # remove basic markdown formatting
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)

    # keep link text only
    text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)

    # normalize whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# ---------------- LIST CLEAN ---------------- #

def _clean_list(items: List[Any], min_len: int = 2) -> List[str]:
    cleaned: List[str] = []

    for item in items or []:
        text = _clean_text(item)
        if text and len(text) >= min_len:
            cleaned.append(text)

    return cleaned


# ---------------- PARAGRAPH ---------------- #

def enrich_paragraph(text: str) -> Dict[str, Any] | None:
    """
    Keep paragraph structure minimal and safe.
    """
    text = _clean_text(text)

    if not text or len(text) < 3:
        return None

    return {
        "type": "paragraph",
        "text": text,
    }


# ---------------- CODE ---------------- #

def enrich_code(text: str, language: str = "") -> Dict[str, Any] | None:
    code = (text or "").strip()

    if not code:
        return None

    return {
        "type": "code",
        "language": (language or "").strip(),
        "text": code,
    }


# ---------------- LIST NORMALIZER ---------------- #

def enrich_list(block: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize list blocks safely.
    """
    if not block:
        return block

    if block.get("type") == "list":
        block["items"] = _clean_list(block.get("items", []))
        return block

    return block


# ---------------- TABLE ---------------- #

def _process_table(item: Dict[str, Any]) -> List[str]:
    rows = item.get("row_text", []) or []
    cleaned: List[str] = []

    for row in rows:
        text = _clean_text(row)
        if text and len(text) >= 4:
            cleaned.append(text)

    return cleaned


# ---------------- PARAGRAPH SPLIT ---------------- #

def _split_paragraph(text: str) -> List[str]:
    """
    Break long text into retrieval-friendly units.
    Purely structural, no domain assumptions.
    """

    # sentence split
    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    # keep short paragraphs intact
    if len(sentences) <= 2:
        return [text]

    return sentences


# ---------------- BUILD SECTION TEXT ---------------- #

def build_section_text(content: List[Dict[str, Any]]) -> str:
    """
    Preserve structure. Do NOT flatten meaning.
    """

    parts: List[str] = []

    for item in content:
        if not item:
            continue

        t = item.get("type")

        # ---------------- PARAGRAPH ---------------- #

        if t == "paragraph":
            text = _clean_text(item.get("text", ""))
            if text:
                parts.append(text)
            continue

        # ---------------- LIST ---------------- #

        if t == "list":
            items = _clean_list(item.get("items", []))
            if not items:
                continue

            # 🔥 preserve list structure explicitly
            if item.get("ordered"):
                for i, it in enumerate(items):
                    parts.append(f"{i+1}. {it}")
            else:
                for it in items:
                    parts.append(f"- {it}")

            continue

        # ---------------- TABLE ---------------- #

        if t in {"table", "generic_table"}:
            rows = item.get("rows", [])

            for row in rows:
                if isinstance(row, dict):
                    line = " | ".join(str(v) for v in row.values())
                else:
                    line = " | ".join(str(v) for v in row)

                line = _clean_text(line)

                if line:
                    parts.append(line)

            continue

        # ---------------- CODE ---------------- #

        if t == "code":
            code_text = item.get("text", "").strip()
            if code_text:
                parts.append(code_text)
            continue

        # ---------------- FALLBACK ---------------- #

        if "text" in item:
            fallback = _clean_text(item.get("text", ""))
            if fallback:
                parts.append(fallback)

    return "\n\n".join(parts).strip()