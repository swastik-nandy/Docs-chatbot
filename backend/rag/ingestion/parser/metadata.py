#--------------------------------------METADATA ENRICHER-------------------------------------------

import re
from typing import Dict, Any, List, Optional


STOPWORDS = {
    "this", "that", "with", "have", "from", "using", "into", "your",
    "will", "when", "where", "what", "which", "then", "than", "also",
    "more", "only", "used", "like", "such", "these", "those",
}


_PLACEHOLDER_HEADINGS = {
    "",
    "root",
}


# ---------------- TEXT UTILS ---------------- #

def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _normalize_key(text: str) -> str:
    return _normalize(text).lower()


def _tokenize_words(text: str) -> List[str]:
    return re.findall(r"\b[a-zA-Z][a-zA-Z0-9._-]{2,}\b", (text or "").lower())


def extract_keywords(text: str, limit: int = 12) -> List[str]:
    """
    Generic keyword extraction:
    - no domain assumptions
    - no target-word dependency
    - keeps useful repeated lexical signals
    """
    words = _tokenize_words(text)
    words = [w for w in words if w not in STOPWORDS]

    seen = set()
    result: List[str] = []

    for word in words:
        if word not in seen:
            result.append(word)
            seen.add(word)

    return result[:limit]


# ---------------- STRUCTURAL HELPERS ---------------- #

def _content_types(content: List[Dict[str, Any]]) -> set[str]:
    return {item.get("type", "") for item in content if item}


def _has_type(content: List[Dict[str, Any]], *types: str) -> bool:
    present = _content_types(content)
    return any(t in present for t in types)


def _count_type(content: List[Dict[str, Any]], *types: str) -> int:
    return sum(1 for item in content if item.get("type") in types)


def _word_count(text: str) -> int:
    return len((text or "").split())


def _is_placeholder_heading(text: str) -> bool:
    return _normalize_key(text) in _PLACEHOLDER_HEADINGS


def _safe_heading_path(path: List[str]) -> List[str]:
    """
    Keep only meaningful path nodes.
    """
    clean = []

    for part in path or []:
        part = _normalize(part)
        if not part:
            continue
        if _is_placeholder_heading(part):
            continue
        clean.append(part)

    return clean


def _first_non_placeholder(parts: List[str]) -> Optional[str]:
    for part in parts:
        normalized = _normalize(part)
        if normalized and not _is_placeholder_heading(normalized):
            return normalized
    return None


# ---------------- CONTEXT ---------------- #

def build_context(path: List[str], heading: str) -> str:
    """
    Context should represent parent hierarchy only.
    It should not simply echo the heading.
    """
    clean_path = _safe_heading_path(path)

    if clean_path:
        return " > ".join(clean_path)

    return "root"


# ---------------- STRUCTURAL PROFILE ---------------- #

def build_structure_profile(content: List[Dict[str, Any]], text: str) -> Dict[str, Any]:
    """
    Generic structural profile of a section.
    No domain or keyword dependency.
    """
    block_types = _content_types(content)

    return {
        "block_count": len(content),
        "block_types": sorted(block_types),
        "paragraph_count": _count_type(content, "paragraph"),
        "table_count": _count_type(content, "table", "generic_table"),
        "list_count": _count_type(content, "list", "bullets", "options", "procedure", "navigation"),
        "code_count": _count_type(content, "code"),
        "word_count": _word_count(text),
        "is_mixed": len(block_types) > 1,
    }


# ---------------- CONTENT ROLE ---------------- #

def detect_content_role(content: List[Dict[str, Any]]) -> str:
    """
    Broad structural role only.
    """
    has_table = _has_type(content, "table", "generic_table")
    has_code = _has_type(content, "code")
    has_list = _has_type(content, "list", "bullets", "options", "procedure", "navigation")
    has_paragraph = _has_type(content, "paragraph")

    role_count = sum([has_table, has_code, has_list, has_paragraph])

    if role_count > 1:
        return "mixed"

    if has_table:
        return "table"

    if has_code:
        return "code"

    if has_list:
        return "list"

    return "text"


# ---------------- SECTION TYPE ---------------- #

def detect_section_type(
    heading: str,
    path: List[str],
    content: List[Dict[str, Any]],
    text: str,
) -> str:
    """
    Structural section typing only.
    No target words, no domain-specific logic.
    """
    has_table = _has_type(content, "table", "generic_table")
    has_code = _has_type(content, "code")
    has_list = _has_type(content, "list", "bullets", "options", "procedure", "navigation")
    has_paragraph = _has_type(content, "paragraph")

    block_types = _content_types(content)
    word_count = _word_count(text)

    if has_table and len(block_types) == 1:
        return "structured_data"

    if has_code and len(block_types) == 1:
        return "code_block"

    if has_list and len(block_types) == 1:
        return "list_block"

    if has_paragraph and len(block_types) == 1:
        return "narrative"

    if len(block_types) > 1:
        return "mixed"

    if word_count < 12:
        return "short"

    return "general"


# ---------------- OPTIONAL CONTEXT ENTITY ---------------- #

def extract_local_context(path: List[str], heading: str) -> Optional[str]:
    """
    Generic local context extractor.

    This is NOT domain-specific and does not try to infer commands/options/etc.
    It simply returns the most local meaningful label.
    """
    heading = _normalize(heading)

    if heading and not _is_placeholder_heading(heading):
        return heading

    clean_path = list(reversed(_safe_heading_path(path)))
    return _first_non_placeholder(clean_path)


# ---------------- MAIN ---------------- #

def enrich_metadata(section: Dict[str, Any]) -> Dict[str, Any]:
    text = section.get("text", "")
    path = section.get("path", [])
    heading = section.get("heading", "")
    content = section.get("content", [])

    clean_path = _safe_heading_path(path)
    context = build_context(clean_path, heading)

    section_type = detect_section_type(
        heading=heading,
        path=clean_path,
        content=content,
        text=text,
    )

    content_role = detect_content_role(content)
    local_context = extract_local_context(clean_path, heading)
    structure_profile = build_structure_profile(content, text)

    section["context"] = context

    # legacy compatibility
    section["type"] = section_type

    # explicit semantic fields
    section["section_type"] = section_type
    section["content_role"] = content_role
    section["local_context"] = local_context
    section["heading_path"] = clean_path
    section["keywords"] = extract_keywords(text)
    section["structure_profile"] = structure_profile

    return section