# rag/ingestion/parser/adapters/mdx_adapter.py

import re
from typing import Dict, List, Tuple


# ---------------- PATTERNS ---------------- #

FENCE_RE = re.compile(
    r"(```[\s\S]*?```|~~~[\s\S]*?~~~)",
    re.MULTILINE,
)

IMPORT_RE = re.compile(
    r"^\s*import\s+.*$",
    re.MULTILINE,
)

HTML_COMMENT_RE = re.compile(
    r"<!--[\s\S]*?-->",
    re.MULTILINE,
)

JSX_COMMENT_RE = re.compile(
    r"\{/\*[\s\S]*?\*/\}",
    re.MULTILINE,
)

SELF_CLOSING_COMPONENT_RE = re.compile(
    r"<([A-Z][A-Za-z0-9_.]*)\b([^<>]*)/>",
    re.MULTILINE,
)

OPEN_COMPONENT_RE = re.compile(
    r"<([A-Z][A-Za-z0-9_.]*)\b([^<>]*)>",
    re.MULTILINE,
)

CLOSE_COMPONENT_RE = re.compile(
    r"</([A-Z][A-Za-z0-9_.]*)>",
    re.MULTILINE,
)

PROP_RE = re.compile(
    r"([A-Za-z_:][A-Za-z0-9_:.-]*)\s*=\s*(\"[^\"]*\"|'[^']*'|\{[^{}]*\})"
)

JSX_EXPRESSION_RE = re.compile(
    r"\{([^{}\n]+)\}",
    re.MULTILINE,
)


# ---------------- MARKERS ---------------- #

COMPONENT_OPEN_MARKER = "::mdx-component-open"
COMPONENT_CLOSE_MARKER = "::mdx-component-close"
COMPONENT_SELF_MARKER = "::mdx-component-self"


# ---------------- CODE FENCE PROTECTION ---------------- #

def _protect_fences(text: str) -> Tuple[str, Dict[str, str]]:
    """
    Temporarily replace fenced code blocks.

    This prevents MDX/JSX cleanup from corrupting code examples.
    """

    store: Dict[str, str] = {}

    def repl(match: re.Match) -> str:
        key = f"@@MDX_FENCE_{len(store)}@@"
        store[key] = match.group(0)
        return key

    protected = FENCE_RE.sub(repl, text or "")
    return protected, store


def _restore_fences(text: str, store: Dict[str, str]) -> str:
    for key, value in store.items():
        text = text.replace(key, value)

    return text


# ---------------- BASIC CLEANUP ---------------- #

def _remove_comments(text: str) -> str:
    text = HTML_COMMENT_RE.sub("", text)
    text = JSX_COMMENT_RE.sub("", text)
    return text


def _remove_imports(text: str) -> str:
    """
    Remove import lines.

    Imports are execution/build-layer details. They usually do not answer
    user questions directly, and keeping them can pollute retrieval.
    """

    return IMPORT_RE.sub("", text)


def _remove_export_blocks(text: str) -> str:
    """
    Remove export declarations conservatively.

    Handles common MDX patterns:
    - export const x = ...
    - export const x = { ... }
    - export default ...
    """

    lines = text.splitlines()
    output: List[str] = []

    skipping = False
    brace_depth = 0

    for line in lines:
        stripped = line.strip()

        if not skipping and stripped.startswith("export "):
            # Multiline export block.
            if "{" in line and not stripped.endswith(";"):
                skipping = True
                brace_depth = line.count("{") - line.count("}")
                continue

            # Single-line export.
            continue

        if skipping:
            brace_depth += line.count("{") - line.count("}")

            if brace_depth <= 0:
                skipping = False
                brace_depth = 0

            continue

        output.append(line)

    return "\n".join(output)


def _remove_execution_layer(text: str) -> str:
    text = _remove_comments(text)
    text = _remove_imports(text)
    text = _remove_export_blocks(text)
    return text


# ---------------- PROP HANDLING ---------------- #

def _clean_prop_value(value: str) -> str:
    value = (value or "").strip()

    if not value:
        return ""

    if value.startswith(("\"", "'")) and value.endswith(("\"", "'")):
        return value[1:-1].strip()

    if value.startswith("{") and value.endswith("}"):
        inner = value[1:-1].strip()

        if inner.startswith(("\"", "'")) and inner.endswith(("\"", "'")):
            return inner[1:-1].strip()

        # Keep simple literal expressions.
        if re.match(r"^[A-Za-z0-9_.$:/\-\s]+$", inner):
            return inner.strip()

        # Complex JS expressions are intentionally not evaluated.
        return ""

    return value


def _extract_props(raw_props: str) -> Dict[str, str]:
    props: Dict[str, str] = {}

    for key, value in PROP_RE.findall(raw_props or ""):
        cleaned = _clean_prop_value(value)

        if cleaned:
            props[key] = cleaned

    return props


def _serialize_props(props: Dict[str, str]) -> str:
    """
    Serialize props into a simple marker-safe format.

    Format:
        key="value" key2="value2"

    Quotes inside values are normalized to avoid breaking parser markers.
    """

    parts: List[str] = []

    for key, value in props.items():
        safe_value = str(value).replace('"', "'").strip()
        parts.append(f'{key}="{safe_value}"')

    return " ".join(parts)


# ---------------- COMPONENT MARKERS ---------------- #

def _component_open_marker(name: str, props: Dict[str, str]) -> str:
    prop_text = _serialize_props(props)

    if prop_text:
        return f'\n\n{COMPONENT_OPEN_MARKER} name="{name}" {prop_text}\n\n'

    return f'\n\n{COMPONENT_OPEN_MARKER} name="{name}"\n\n'


def _component_close_marker(name: str) -> str:
    return f'\n\n{COMPONENT_CLOSE_MARKER} name="{name}"\n\n'


def _component_self_marker(name: str, props: Dict[str, str]) -> str:
    prop_text = _serialize_props(props)

    if prop_text:
        return f'\n\n{COMPONENT_SELF_MARKER} name="{name}" {prop_text}\n\n'

    return f'\n\n{COMPONENT_SELF_MARKER} name="{name}"\n\n'


def _replace_self_closing_component(match: re.Match) -> str:
    name = match.group(1)
    raw_props = match.group(2) or ""
    props = _extract_props(raw_props)

    return _component_self_marker(name, props)


def _replace_open_component(match: re.Match) -> str:
    name = match.group(1)
    raw_props = match.group(2) or ""
    props = _extract_props(raw_props)

    return _component_open_marker(name, props)


def _replace_close_component(match: re.Match) -> str:
    name = match.group(1)

    return _component_close_marker(name)


def _normalize_components(text: str) -> str:
    """
    Convert MDX component syntax into explicit Markdown-safe markers.

    This preserves structure without knowing anything about specific components.
    """

    text = SELF_CLOSING_COMPONENT_RE.sub(_replace_self_closing_component, text)
    text = OPEN_COMPONENT_RE.sub(_replace_open_component, text)
    text = CLOSE_COMPONENT_RE.sub(_replace_close_component, text)

    return text


# ---------------- JSX EXPRESSION CLEANUP ---------------- #

def _normalize_jsx_expressions(text: str) -> str:
    """
    Normalize simple inline JSX expressions.

    We do not evaluate JavaScript.

    Kept:
    - {"literal"}
    - {'literal'}
    - {simple.identifier}
    - {simple/path-like/value}

    Removed:
    - complex JS expressions
    - object/array/function expressions
    """

    def repl(match: re.Match) -> str:
        inner = (match.group(1) or "").strip()

        if not inner:
            return ""

        if inner.startswith(("\"", "'")) and inner.endswith(("\"", "'")):
            return inner[1:-1]

        if re.match(r"^[A-Za-z0-9_.$:/\-]+$", inner):
            return inner

        return ""

    return JSX_EXPRESSION_RE.sub(repl, text)


# ---------------- SPACING ---------------- #

def _cleanup_spacing(text: str) -> str:
    lines = (text or "").splitlines()

    cleaned: List[str] = []
    blank_count = 0

    for line in lines:
        stripped = line.rstrip()

        if not stripped:
            blank_count += 1

            if blank_count <= 2:
                cleaned.append("")

            continue

        blank_count = 0
        cleaned.append(stripped)

    return "\n".join(cleaned).strip() + "\n"


# ---------------- PUBLIC API ---------------- #

def normalize_mdx(text: str) -> str:
    """
    Convert MDX into parser-safe Markdown-like text.

    This function is intentionally domain-agnostic.

    It does not know about:
    - changelogs
    - docs products
    - release components
    - framework-specific components
    - company-specific components

    It only preserves:
    - Markdown content
    - fenced code blocks
    - component boundaries
    - component names
    - component props

    Output includes marker lines like:

        ::mdx-component-open name="ComponentName" prop="value"
        ::mdx-component-close name="ComponentName"
        ::mdx-component-self name="ComponentName" prop="value"

    The AST parser should later recognize these markers as component events.
    """

    if not text:
        return ""

    protected, fences = _protect_fences(text)

    protected = _remove_execution_layer(protected)
    protected = _normalize_components(protected)
    protected = _normalize_jsx_expressions(protected)

    restored = _restore_fences(protected, fences)
    restored = _cleanup_spacing(restored)

    return restored