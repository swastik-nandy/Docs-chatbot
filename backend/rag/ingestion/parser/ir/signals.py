# rag/ingestion/parser/ir/signals.py

import re
from typing import Dict, List


# ---------------- REGEX PATTERNS ---------------- #

FLAG_RE = re.compile(
    r"(^|\s)(--[a-zA-Z0-9][a-zA-Z0-9-]*|-[a-zA-Z])(\s|=|$)"
)

KEY_VALUE_RE = re.compile(
    r"^[`'\"]?[a-zA-Z0-9_.\-/ ]+[`'\"]?\s*[:=]\s*.+$"
)

LABEL_RE = re.compile(
    r"^(?P<label>[`'\"]?[A-Za-z][A-Za-z0-9 ._/\-]{1,70}[`'\"]?)\s*:\s*(?P<body>.+)$"
)

PATH_RE = re.compile(
    r"(^|[\s`'\"])(\.{0,2}/|/|[a-zA-Z0-9_.\-]+/)[a-zA-Z0-9_./\-]+"
)

ASSIGNMENT_RE = re.compile(
    r"\b[a-zA-Z_][a-zA-Z0-9_]*\s*=\s*[^,\s]+"
)

MERGE_CONFLICT_RE = re.compile(
    r"^(<<<<<<<|=======|>>>>>>>)"
)

CODE_SYMBOLS = {"=", "{", "}", "|", ">", "<", "$", "`"}


COMMON_SENTENCE_STARTERS = {
    "the", "this", "that", "these", "those",
    "our", "your", "their", "its",
    "a", "an",
    "when", "where", "what", "which", "why", "how",
    "if", "to", "for", "in", "on", "with", "without",
}


ACTION_STARTERS = {
    "add", "analyze", "apply", "ask", "build", "check", "choose",
    "collect", "compare", "configure", "confirm", "copy", "create",
    "delete", "deploy", "disable", "enable", "fetch", "find", "fix",
    "generate", "import", "include", "install", "keep", "list",
    "look", "make", "move", "open", "prefer", "provide", "remove",
    "replace", "report", "review", "run", "scan", "search", "set",
    "show", "strip", "summarize", "update", "use", "validate",
    "verify", "write",
}


DIRECTIVE_STARTERS = {
    "do", "do not", "don’t", "dont", "never", "always", "avoid",
    "ensure", "prefer", "remember",
}


# ---------------- HELPERS ---------------- #

def _words(text: str) -> List[str]:
    return [word for word in re.split(r"\s+", (text or "").strip()) if word]


def _clean_token(token: str) -> str:
    return re.sub(r"^[`'\"(*\[]+|[`'\":,.;!?)*\]]+$", "", token or "")


def _first_word(text: str) -> str:
    words = _words(text)
    if not words:
        return ""
    return _clean_token(words[0])


def _first_two_words(text: str) -> str:
    words = [_clean_token(w).lower() for w in _words(text)[:2]]
    return " ".join(w for w in words if w)


def _starts_with_action(text: str) -> bool:
    first = _first_word(text).lower()
    return first in ACTION_STARTERS


def _starts_with_directive(text: str) -> bool:
    first = _first_word(text).lower()
    first_two = _first_two_words(text)
    return first in DIRECTIVE_STARTERS or first_two in DIRECTIVE_STARTERS


def _looks_like_sentence(text: str) -> bool:
    """
    Conservative prose detector.
    Prevents normal documentation prose from being classified as commands.
    """

    text = (text or "").strip()
    words = _words(text)

    if not text or not words:
        return False

    first = _first_word(text)

    if text.endswith((".", "!", "?")):
        return True

    if first.lower() in COMMON_SENTENCE_STARTERS:
        return True

    if first[:1].isupper() and len(words) >= 4:
        return True

    return False


def _has_cli_prefix(text: str) -> bool:
    stripped = (text or "").strip()
    return stripped.startswith(("$ ", "> ", "# "))


def _has_command_shape(text: str) -> bool:
    """
    Detect executable-like command shape without product-specific rules.
    """

    stripped = (text or "").strip()
    words = _words(stripped)

    if len(words) < 2:
        return False

    if _looks_like_sentence(stripped):
        return False

    first = _clean_token(words[0])

    if not first:
        return False

    if len(words) > 12:
        return False

    if first.lower() in COMMON_SENTENCE_STARTERS:
        return False

    if _has_cli_prefix(stripped):
        return True

    if FLAG_RE.search(stripped):
        return True

    if PATH_RE.search(stripped):
        return True

    if ASSIGNMENT_RE.search(stripped):
        return True

    executable_like = bool(
        re.match(r"^(\./|/)?[a-z0-9][a-z0-9_.\-/]*$", first)
    )

    if not executable_like:
        return False

    lowered_words = [_clean_token(w).lower() for w in words[:3]]
    if any(w in COMMON_SENTENCE_STARTERS for w in lowered_words):
        return False

    return True


def _extract_label(text: str) -> str:
    match = LABEL_RE.match((text or "").strip())
    if not match:
        return ""

    label = match.group("label") or ""
    return _clean_token(label).strip()


def _is_labeled_action(text: str) -> bool:
    """
    Detect patterns like:
    - Validate: Check that the file exists
    - Move the file: Use git mv
    - Report: List all modified files

    But avoid classifying:
    - Efficient: we don't want to waste time
    - Arguments: $ARGUMENTS
    - Product name: always X
    """

    match = LABEL_RE.match((text or "").strip())
    if not match:
        return False

    label = (match.group("label") or "").strip()
    body = (match.group("body") or "").strip()

    if not label or not body:
        return False

    label_words = _words(label)
    body_words = _words(body)

    if len(label_words) > 6:
        return False

    if not body_words:
        return False

    # Action in the label itself: "Move the file: ..."
    if _starts_with_action(label):
        return True

    # Action or directive in the body: "Validate: Check that ..."
    if _starts_with_action(body) or _starts_with_directive(body):
        return True

    return False


# ---------------- CORE DETECTOR ---------------- #

def detect_signals(text: str) -> Dict[str, bool | str]:
    """
    Extract structure-only signals from a text block.

    Principles:
    - no product-specific rules
    - no framework-specific rules
    - conservative command detection
    - useful for prose, CLI, config, tables, lists, and MDX-derived text
    """

    if not text:
        return {}

    text = str(text).strip()
    words = _words(text)

    has_flags = bool(FLAG_RE.search(text))
    is_key_value = bool(KEY_VALUE_RE.match(text))
    has_path = bool(PATH_RE.search(text))
    has_assignment = bool(ASSIGNMENT_RE.search(text))
    has_merge_conflict_marker = bool(MERGE_CONFLICT_RE.match(text))

    has_numbers = any(char.isdigit() for char in text)
    has_symbols = any(char in CODE_SYMBOLS for char in text)

    sentence_like = _looks_like_sentence(text)
    starts_with_action = _starts_with_action(text)
    is_directive = _starts_with_directive(text)
    is_labeled_action = _is_labeled_action(text)
    is_command_like = _has_command_shape(text)

    label = _extract_label(text)

    return {
        "is_command_like": bool(is_command_like),
        "starts_with_action": bool(starts_with_action),
        "is_labeled_action": bool(is_labeled_action),
        "is_directive": bool(is_directive),
        "has_flags": bool(has_flags),
        "is_key_value": bool(is_key_value),
        "has_path": bool(has_path),
        "has_assignment": bool(has_assignment),
        "has_merge_conflict_marker": bool(has_merge_conflict_marker),
        "is_short": len(words) <= 8,
        "is_long": len(words) >= 40,
        "has_numbers": bool(has_numbers),
        "has_symbols": bool(has_symbols),
        "sentence_like": bool(sentence_like),
        "label": label,
    }