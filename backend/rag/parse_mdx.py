# rag/test_mdx.py

from collections import Counter
from pprint import pprint

from rag.ingestion.parser.markdown import load_markdown
from rag.ingestion.parser.adapters import normalize_mdx
from rag.ingestion.parser.cleaner import clean_markdown
from rag.ingestion.parser.ast_parser import parse_md_ast
from rag.ingestion.parser import parse


TEST_FILE = "docs/mellisearch/changelog.mdx"


def print_divider(title: str) -> None:
    print("\n" + "=" * 90)
    print(title)
    print("=" * 90)


def preview(text: str, limit: int = 160) -> str:
    text = (text or "").replace("\n", " ").strip()
    return text[:limit] + ("..." if len(text) > limit else "")


def inspect_pipeline_stages() -> None:
    print_divider("1. MDX PIPELINE STAGES")

    raw = load_markdown(TEST_FILE)
    normalized = normalize_mdx(raw)
    cleaned = clean_markdown(normalized)
    elements = parse_md_ast(cleaned)

    type_counts = Counter(el.get("type", "unknown") for el in elements)

    component_events = [
        el for el in elements
        if el.get("type") in {
            "component_open",
            "component_close",
            "component_self",
        }
    ]

    print(f"File                : {TEST_FILE}")
    print(f"Raw chars           : {len(raw)}")
    print(f"Normalized chars    : {len(normalized)}")
    print(f"Cleaned chars       : {len(cleaned)}")
    print(f"AST elements        : {len(elements)}")
    print(f"AST type counts     : {dict(type_counts)}")
    print(f"Component events    : {len(component_events)}")

    print_divider("2. FIRST 30 COMPONENT EVENTS")

    if not component_events:
        print("❌ No component events found.")
        print("   Problem is likely in mdx_adapter.py or ast_parser.py.")
        return

    for index, event in enumerate(component_events[:30]):
        print(f"\n[{index}]")
        pprint(event)

    if len(component_events) > 30:
        print(f"\n... and {len(component_events) - 30} more component events")


def inspect_full_parse() -> None:
    print_divider("3. FULL PARSE OUTPUT")

    docs = parse(TEST_FILE)

    if not docs:
        print("❌ parse() returned no documents")
        return

    doc = docs[0]
    sections = doc.metadata.get("ast", [])

    print(f"File       : {doc.metadata.get('file_name')}")
    print(f"Doc type   : {doc.metadata.get('doc_type')}")
    print(f"Sections   : {len(sections)}")
    print(f"Text chars : {len(doc.text or '')}")

    section_component_count = sum(
        1 for section in sections
        if section.get("component_stack") or section.get("component_context")
    )

    block_component_count = sum(
        1
        for section in sections
        for block in section.get("blocks", [])
        if (
            block.get("meta", {}).get("component_stack")
            or block.get("meta", {}).get("component_context")
        )
    )

    print(f"Sections with component context : {section_component_count}")
    print(f"Blocks with component context   : {block_component_count}")

    print_divider("4. FIRST 12 SECTIONS")

    for index, section in enumerate(sections[:12]):
        blocks = section.get("blocks", [])

        print(f"\n--- SECTION {index} ---")
        print("Heading           :", section.get("heading"))
        print("Context           :", section.get("context"))
        print("Section ID        :", section.get("section_id"))
        print("Component stack   :", section.get("component_stack"))
        print("Component context :", section.get("component_context"))
        print("Content types     :", [item.get("type") for item in section.get("content", [])])
        print("Blocks            :", len(blocks))

        for block in blocks[:3]:
            meta = block.get("meta", {}) or {}

            print(
                "  -",
                block.get("id"),
                "|",
                block.get("type"),
                "|",
                block.get("function"),
                "|",
                preview(block.get("text", ""), 120),
            )

            if meta.get("component_stack") or meta.get("component_context"):
                print("    component_stack   :", meta.get("component_stack"))
                print("    component_context :", meta.get("component_context"))

            retrieval_text = block.get("retrieval_text", "")
            if retrieval_text:
                print("    retrieval_text    :", preview(retrieval_text, 180))


def main() -> None:
    inspect_pipeline_stages()
    inspect_full_parse()


if __name__ == "__main__":
    main()