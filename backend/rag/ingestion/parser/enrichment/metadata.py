# --------------------------------------METADATA ENRICHER-------------------------------------------

import re
from typing import Dict, Any, List, Optional


STOPWORDS = {
    "this", "that", "with", "have", "from", "using", "into", "your",
    "will", "when", "where", "what", "which", "then", "than", "also",
    "more", "only", "used", "like", "such", "these", "those",
}


# ---------------- TEXT UTILS ---------------- #

def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _tokenize_words(text: str) -> List[str]:
    return re.findall(r"\b[a-zA-Z][a-zA-Z0-9._-]{3,}\b", (text or "").lower())


def extract_keywords(text: str, limit: int = 12) -> List[str]:
    """
    Lightweight keyword extraction (purely statistical, no domain logic)
    """
    words = _tokenize_words(text)
    words = [w for w in words if w not in STOPWORDS]

    seen = set()
    result = []

    for w in words:
        if w not in seen:
            result.append(w)
            seen.add(w)

    return result[:limit]


# ---------------- STRUCTURAL SIGNALS ---------------- #

def _content_types(content: List[Dict[str, Any]]) -> set[str]:
    return {item.get("type", "") for item in content if item}


# ---------------- COMMAND-LIKE DETECTION (STRUCTURAL) ---------------- #

_CODEISH_RE = re.compile(r"`([^`]+)`")
_OPTION_TOKEN_RE = re.compile(r"(--[a-zA-Z0-9][a-zA-Z0-9-]*|-[a-zA-Z])")


def _is_command_like(text: str) -> bool:
    text = _normalize(text)

    if not text:
        return False

    if len(text.split()) > 6:
        return False

    if _OPTION_TOKEN_RE.search(text):
        return False

    if any(sym in text for sym in ["|", ">", "<", "=", "{", "}"]):
        return False

    return True


def _extract_command_context(path: List[str], heading: str) -> Optional[str]:
    """
    Extract command-like anchor without assuming domain.
    """
    candidates = [heading] + list(reversed(path))

    for candidate in candidates:
        for code in _CODEISH_RE.findall(candidate or ""):
            if _is_command_like(code):
                return _normalize(code)

        if _is_command_like(candidate):
            return _normalize(candidate)

    return None


# ---------------- SECTION TYPE (PURE STRUCTURE) ---------------- #

def detect_section_type(
    heading: str,
    path: List[str],
    content: List[Dict[str, Any]]
) -> str:
    """
    STRICTLY structure-based classification.
    NO keyword inference.
    """

    types = _content_types(content)

    if "procedure" in types:
        return "procedure"

    if "table" in types or "generic_table" in types:
        return "structured"

    if "code" in types:
        return "code"

    if "bullets" in types or "list" in types:
        return "list"

    if len(types) > 1:
        return "mixed"

    return "text"


# ---------------- CONTENT ROLE ---------------- #

def detect_content_role(content: List[Dict[str, Any]]) -> str:
    types = _content_types(content)

    if "generic_table" in types or "table" in types:
        return "table"

    if "procedure" in types:
        return "procedure"

    if "code" in types:
        return "code"

    if "bullets" in types or "list" in types:
        return "list"

    return "text"


# ---------------- CONTEXT ---------------- #

def build_context(path: List[str], heading: str) -> str:
    clean_path = [p for p in path if p and p.lower() != "root"]

    if clean_path:
        return " > ".join(clean_path)

    return heading or "root"


# ---------------- MAIN ---------------- #

def enrich_metadata(section: Dict[str, Any]) -> Dict[str, Any]:
    """
    Attach structural metadata to section.
    No domain-specific inference.
    """

    text = section.get("text", "")
    path = section.get("path", [])
    heading = section.get("heading", "")
    content = section.get("content", [])

    section["context"] = build_context(path, heading)
    section["section_type"] = detect_section_type(heading, path, content)
    section["content_role"] = detect_content_role(content)
    section["command_context"] = _extract_command_context(path, heading)
    section["heading_path"] = path
    section["keywords"] = extract_keywords(text)

    return section