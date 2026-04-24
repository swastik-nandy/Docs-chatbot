# --------------------------------------CLEAN MARKDOWN / MDX AST PARSER-------------------------------------------

import re
from typing import Dict, List

from markdown_it import MarkdownIt


md = MarkdownIt("gfm-like", {"linkify": False})


# ---------------- MDX COMPONENT MARKERS ---------------- #

COMPONENT_OPEN_PREFIX = "::mdx-component-open"
COMPONENT_CLOSE_PREFIX = "::mdx-component-close"
COMPONENT_SELF_PREFIX = "::mdx-component-self"

MARKER_RE = re.compile(
    r'^::mdx-component-(open|close|self)\s+(?P<attrs>.*)$'
)

ATTR_RE = re.compile(
    r'([A-Za-z_:][A-Za-z0-9_:.-]*)="([^"]*)"'
)


# ---------------- BASIC HELPERS ---------------- #

def _clean(text: str) -> str:
    return (text or "").strip()


def _parse_marker_attrs(raw: str) -> Dict[str, str]:
    """
    Parse marker attrs emitted by mdx_adapter.py.

    Example:
        name="Update" label="v1.42" description="2026-04-13"

    Returns:
        {
            "name": "Update",
            "label": "v1.42",
            "description": "2026-04-13"
        }
    """

    attrs: Dict[str, str] = {}

    for key, value in ATTR_RE.findall(raw or ""):
        attrs[key] = value

    return attrs


def _parse_component_marker(text: str):
    """
    Convert MDX component marker line into AST event.

    Returns:
        dict or None
    """

    text = _clean(text)

    if not text.startswith("::mdx-component-"):
        return None

    match = MARKER_RE.match(text)

    if not match:
        return None

    marker_kind = match.group(1)
    attrs = _parse_marker_attrs(match.group("attrs") or "")

    name = attrs.pop("name", "")

    if marker_kind == "open":
        return {
            "type": "component_open",
            "name": name,
            "props": attrs,
        }

    if marker_kind == "close":
        return {
            "type": "component_close",
            "name": name,
            "props": attrs,
        }

    if marker_kind == "self":
        return {
            "type": "component_self",
            "name": name,
            "props": attrs,
        }

    return None


def _is_component_marker_text(text: str) -> bool:
    return _parse_component_marker(text) is not None


# ---------------- MAIN PARSER ---------------- #

def parse_md_ast(text: str):
    """
    Parse Markdown / normalized-MDX into a clean structural AST.

    Emits:
    - heading
    - paragraph
    - list
    - table
    - code
    - component_open
    - component_close
    - component_self

    Important:
    - Preserves ordered vs unordered list structure
    - Preserves tables
    - Preserves fenced/code blocks
    - Preserves normalized MDX component markers
    - Does not add domain-specific meaning
    """

    tokens = md.parse(text)
    elements = []

    # ---------------- STATE ---------------- #

    paragraph_buffer: List[str] = []
    in_paragraph = False

    heading_level = None

    # LIST
    in_list = False
    current_list: List[str] = []
    current_item: List[str] = []
    current_list_ordered = False

    # TABLE
    in_table = False
    current_table: List[List[str]] = []
    current_row: List[str] = []
    current_cell: List[str] = []

    # ---------------- FLUSH HELPERS ---------------- #

    def flush_paragraph():
        nonlocal paragraph_buffer, in_paragraph

        if paragraph_buffer:
            content = _clean(" ".join(paragraph_buffer))

            if content:
                marker = _parse_component_marker(content)

                if marker:
                    elements.append(marker)
                else:
                    elements.append({
                        "type": "paragraph",
                        "text": content,
                    })

        paragraph_buffer = []
        in_paragraph = False

    def flush_list():
        nonlocal current_list, current_list_ordered

        if current_list:
            elements.append({
                "type": "list",
                "items": current_list,
                "ordered": current_list_ordered,
            })

        current_list = []
        current_list_ordered = False

    def flush_list_item():
        nonlocal current_item, current_list

        if current_item:
            content = _clean(" ".join(current_item))

            if content:
                marker = _parse_component_marker(content)

                if marker:
                    # Component markers should remain structural events,
                    # not list items.
                    elements.append(marker)
                else:
                    current_list.append(content)

        current_item = []

    def flush_cell():
        nonlocal current_cell, current_row

        cell_text = _clean(" ".join(current_cell))
        current_row.append(cell_text)
        current_cell = []

    def flush_row():
        nonlocal current_row, current_table

        if current_row:
            current_table.append(current_row)

        current_row = []

    def flush_table():
        nonlocal current_table

        if current_table:
            elements.append({
                "type": "table",
                "rows": current_table,
            })

        current_table = []

    def close_open_paragraph_and_list():
        flush_paragraph()
        flush_list_item()
        flush_list()

    def close_all():
        flush_paragraph()
        flush_list_item()
        flush_list()

        if in_table:
            flush_cell()
            flush_row()
            flush_table()

    # ---------------- MAIN LOOP ---------------- #

    for token in tokens:
        t = token.type

        # ---------------- HEADINGS ---------------- #

        if t == "heading_open":
            close_all()
            heading_level = int(token.tag[1])
            continue

        if t == "heading_close":
            heading_level = None
            continue

        if t == "inline" and heading_level is not None:
            txt = _clean(token.content)

            if txt:
                marker = _parse_component_marker(txt)

                if marker:
                    elements.append(marker)
                else:
                    elements.append({
                        "type": "heading",
                        "level": heading_level,
                        "text": txt,
                    })

            continue

        # ---------------- TABLE ---------------- #

        if t == "table_open":
            close_open_paragraph_and_list()
            in_table = True
            current_table = []
            continue

        if t == "tr_open" and in_table:
            current_row = []
            continue

        if t in {"td_open", "th_open"} and in_table:
            current_cell = []
            continue

        if t == "inline" and in_table:
            txt = _clean(token.content)

            if txt:
                current_cell.append(txt)

            continue

        if t in {"td_close", "th_close"} and in_table:
            flush_cell()
            continue

        if t == "tr_close" and in_table:
            flush_row()
            continue

        if t == "table_close":
            flush_table()
            in_table = False
            continue

        # ---------------- LIST ---------------- #

        if t in {"bullet_list_open", "ordered_list_open"}:
            flush_paragraph()
            flush_list_item()
            flush_list()

            in_list = True
            current_list = []
            current_item = []
            current_list_ordered = t == "ordered_list_open"
            continue

        if t == "list_item_open" and in_list:
            current_item = []
            continue

        if t == "list_item_close" and in_list:
            flush_list_item()
            continue

        if t in {"bullet_list_close", "ordered_list_close"} and in_list:
            flush_list_item()
            flush_list()
            in_list = False
            continue

        # ---------------- PARAGRAPH ---------------- #

        if t == "paragraph_open":
            if in_list:
                # markdown-it wraps list item text in paragraph tokens.
                # We do not want separate paragraph blocks for simple list text.
                continue

            flush_paragraph()
            in_paragraph = True
            paragraph_buffer = []
            continue

        if t == "paragraph_close":
            if in_list:
                continue

            flush_paragraph()
            continue

        # ---------------- INLINE TEXT ---------------- #

        if t == "inline":
            txt = _clean(token.content)

            if not txt:
                continue

            marker = _parse_component_marker(txt)

            if marker:
                # Component markers are structural events.
                # Flush anything currently buffered before adding them.
                flush_paragraph()
                flush_list_item()
                elements.append(marker)
                continue

            if in_list:
                current_item.append(txt)
                continue

            if in_paragraph:
                paragraph_buffer.append(txt)
                continue

            # Inline text outside paragraph/list/table/heading is rare,
            # but preserve it instead of losing source meaning.
            elements.append({
                "type": "paragraph",
                "text": txt,
            })
            continue

        # ---------------- CODE ---------------- #

        if t == "fence":
            close_all()

            code = token.content.rstrip("\n")

            if code.strip():
                elements.append({
                    "type": "code",
                    "language": token.info.strip() if token.info else "",
                    "text": code,
                })

            continue

        if t == "code_block":
            close_all()

            code = token.content.rstrip("\n")

            if code.strip():
                elements.append({
                    "type": "code",
                    "language": "",
                    "text": code,
                })

            continue

    # ---------------- FINAL FLUSH ---------------- #

    close_all()

    return elements