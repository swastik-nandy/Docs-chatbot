# --------------------------------------ENRICHER-------------------------------------------

import re
from typing import Dict, List

from ..heading_builder import update_heading_stack, extract_path
from ..table_parser import parse_table

from ..ir.block_builder import (
    assign_block_identity,
    build_block,
    build_blocks_from_list,
    build_blocks_from_table_rows,
)

from ..ir.relationships import enrich_block_relationships

from .tables import enrich_tables
from .texts import enrich_paragraph, enrich_code, enrich_list, build_section_text
from .metadata import enrich_metadata

from .component_context import (
    attach_to_content_block,
    build_self_closing_component_block,
    current_component_meta,
    effective_local_context,
    merge_into_meta,
    pop_component,
    push_component,
    stack_from_content_or_section,
)


OVERVIEW_HEADING = "Overview"


# --------------------------------------HELPERS-------------------------------------------

def _slug(text: str, fallback: str = "section") -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"`+", "", text)
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text or fallback


def _base_meta(
    item_index: int,
    source_type: str,
    section: Dict,
) -> Dict:
    return {
        "source_type": source_type,
        "source_index": item_index,
        "synthetic_section": section.get("synthetic", False),
    }


# --------------------------------------CORE ENRICHER-------------------------------------------

def enrich(elements):
    """
    Universal Markdown / normalized-MDX enricher.

    Responsibilities:
    - Build heading-based sections
    - Preserve pre-heading content as Overview
    - Preserve paragraphs, lists, tables, code
    - Preserve generic MDX component context
    - Build retrieval-ready IR blocks
    - Assign stable block IDs
    - Link related evidence blocks

    No domain-specific logic.
    """

    sections = []
    current_section = None
    heading_stack = []
    component_stack: List[Dict] = []

    # --------------------------------------SECTION HELPERS-------------------------------------------

    def flush_section():
        nonlocal current_section

        if current_section and current_section.get("content"):
            sections.append(current_section)

        current_section = None

    def start_section(heading_text: str):
        section = {
            "heading": heading_text,
            "path": extract_path(heading_stack[:-1]),
            "content": [],
            "blocks": [],
        }

        if component_stack:
            section.update(current_component_meta(component_stack))

        return section

    def start_overview_section():
        section = {
            "heading": OVERVIEW_HEADING,
            "path": [],
            "content": [],
            "blocks": [],
            "synthetic": True,
            "synthetic_reason": "content_before_first_heading",
        }

        if component_stack:
            section.update(current_component_meta(component_stack))

        return section

    def ensure_section():
        nonlocal current_section

        if current_section is None:
            current_section = start_overview_section()

        if component_stack and not current_section.get("component_stack"):
            current_section.update(current_component_meta(component_stack))

        return current_section

    def add_content_block(block):
        section = ensure_section()

        if block:
            section["content"].append(block)

    # --------------------------------------FIRST PASS: AST EVENTS → SECTIONS-------------------------------------------

    for el in elements:
        if not el:
            continue

        etype = el.get("type")

        # ---------------- MDX COMPONENT EVENTS ---------------- #

        if etype == "component_open":
            push_component(
                component_stack,
                name=el.get("name", ""),
                props=el.get("props", {}) or {},
            )

            if current_section and not current_section.get("component_stack"):
                current_section.update(current_component_meta(component_stack))

            continue

        if etype == "component_close":
            pop_component(
                component_stack,
                name=el.get("name", ""),
            )
            continue

        if etype == "component_self":
            block = build_self_closing_component_block(
                name=el.get("name", ""),
                props=el.get("props", {}) or {},
                stack=component_stack,
            )

            add_content_block(block)
            continue

        # ---------------- HEADING ---------------- #

        if etype == "heading":
            flush_section()

            heading_stack = update_heading_stack(
                heading_stack,
                el.get("level"),
                el.get("text"),
            )

            current_section = start_section(el.get("text", ""))
            continue

        # ---------------- TABLE ---------------- #

        if etype == "table":
            structured = parse_table(el.get("rows", []))

            if structured:
                structured = attach_to_content_block(
                    structured,
                    component_stack,
                )
                add_content_block(structured)

            continue

        # ---------------- LIST ---------------- #

        if etype == "list":
            block = enrich_list({
                "type": "list",
                "items": el.get("items", []),
                "ordered": el.get("ordered", False),
            })

            block = attach_to_content_block(
                block,
                component_stack,
            )

            add_content_block(block)
            continue

        # ---------------- CODE ---------------- #

        if etype == "code":
            block = enrich_code(
                el.get("text", ""),
                el.get("language", ""),
            )

            block = attach_to_content_block(
                block,
                component_stack,
            )

            add_content_block(block)
            continue

        # ---------------- PARAGRAPH ---------------- #

        if etype == "paragraph":
            block = enrich_paragraph(el.get("text", ""))

            block = attach_to_content_block(
                block,
                component_stack,
            )

            add_content_block(block)
            continue

    flush_section()

    # --------------------------------------SECOND PASS: SECTIONS → IR BLOCKS-------------------------------------------

    enriched_sections = []
    doc_id = "doc"

    for section_index, section in enumerate(sections):
        content = section.get("content", [])

        if not content:
            continue

        content = enrich_tables(content)
        section["content"] = content

        section_text = build_section_text(content)

        if not section_text:
            continue

        section["text"] = section_text
        section = enrich_metadata(section)

        heading = section.get("heading", "")
        context = section.get("context", "")

        base_local_context = (
            section.get("local_context")
            or section.get("command_context")
            or heading
        )

        section_id = f"s{section_index}_{_slug(heading)}"
        ir_blocks = []

        for item_index, item in enumerate(content):
            if not item:
                continue

            item_type = item.get("type")
            item_stack = stack_from_content_or_section(item, section)

            local_context = effective_local_context(
                base_local_context=base_local_context,
                stack=item_stack,
            )

            # ---------------- PARAGRAPH → IR BLOCK ---------------- #

            if item_type == "paragraph":
                meta = merge_into_meta(
                    _base_meta(item_index, "paragraph", section),
                    item_stack,
                )

                block = build_block(
                    base_type="text",
                    form="paragraph",
                    text=item.get("text", ""),
                    heading=heading,
                    context=context,
                    local_context=local_context,
                    meta=meta,
                )

                if block:
                    ir_blocks.append(block)

                continue

            # ---------------- LIST → ITEM-LEVEL IR BLOCKS ---------------- #

            if item_type == "list":
                meta = merge_into_meta(
                    {
                        **_base_meta(item_index, "list", section),
                        "ordered": item.get("ordered", False),
                    },
                    item_stack,
                )

                blocks = build_blocks_from_list(
                    items=item.get("items", []),
                    ordered=item.get("ordered", False),
                    heading=heading,
                    context=context,
                    local_context=local_context,
                    meta=meta,
                )

                ir_blocks.extend(blocks)
                continue

            # ---------------- TABLE → ROW-LEVEL IR BLOCKS ---------------- #

            if item_type == "generic_table":
                meta = merge_into_meta(
                    {
                        **_base_meta(item_index, "table", section),
                        "headers": item.get("headers", []),
                        "table_profile": item.get("table_profile", {}),
                        "shape": item.get("shape", {}),
                        "anomalies": item.get("anomalies", []),
                    },
                    item_stack,
                )

                blocks = build_blocks_from_table_rows(
                    row_texts=item.get("row_text", []),
                    heading=heading,
                    context=context,
                    local_context=local_context,
                    meta=meta,
                )

                ir_blocks.extend(blocks)
                continue

            # ---------------- CODE → IR BLOCK ---------------- #

            if item_type == "code":
                meta = merge_into_meta(
                    {
                        **_base_meta(item_index, "code", section),
                        "language": item.get("language", ""),
                    },
                    item_stack,
                )

                block = build_block(
                    base_type="code",
                    form="block",
                    text=item.get("text", ""),
                    heading=heading,
                    context=context,
                    local_context=local_context,
                    meta=meta,
                )

                if block:
                    ir_blocks.append(block)

                continue

            # ---------------- SELF-CLOSING COMPONENT → IR BLOCK ---------------- #

            if item_type == "component":
                meta = merge_into_meta(
                    {
                        **_base_meta(item_index, "component", section),
                        "component_name": item.get("name", ""),
                        "component_props": item.get("props", {}),
                    },
                    item_stack,
                )

                block = build_block(
                    base_type="component",
                    form="block",
                    text=item.get("text", ""),
                    heading=heading,
                    context=context,
                    local_context=local_context,
                    meta=meta,
                )

                if block:
                    ir_blocks.append(block)

                continue

            # ---------------- FALLBACK ---------------- #

            fallback_text = item.get("text", "")

            if fallback_text:
                meta = merge_into_meta(
                    _base_meta(item_index, item_type or "unknown", section),
                    item_stack,
                )

                block = build_block(
                    base_type="text",
                    form="block",
                    text=fallback_text,
                    heading=heading,
                    context=context,
                    local_context=local_context,
                    meta=meta,
                )

                if block:
                    ir_blocks.append(block)

        # ---------------- ID + RELATIONSHIP PASS ---------------- #

        for block_index, block in enumerate(ir_blocks):
            assign_block_identity(
                block=block,
                doc_id=doc_id,
                section_id=section_id,
                block_index=block_index,
            )

        ir_blocks = enrich_block_relationships(ir_blocks)

        section["section_id"] = section_id
        section["blocks"] = ir_blocks
        section["block_count"] = len(ir_blocks)

        enriched_sections.append(section)

    return enriched_sections