# --------------------------------------RELATIONSHIP / EMBEDDING DEBUG-------------------------------------------

from collections import Counter
from pathlib import Path
from dotenv import load_dotenv

from rag.ingestion.parser import parse


load_dotenv()


# --------------------------------------CONFIG-------------------------------------------

TEST_FILES = [
    "docs/fast_api/first_steps.md",
    
]

PREVIEW_LIMIT = 260


# --------------------------------------HELPERS-------------------------------------------

def _divider(title: str) -> None:
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)


def _subdivider(title: str) -> None:
    print("\n" + "-" * 80)
    print(title)
    print("-" * 80)


def _preview(text: str, limit: int = PREVIEW_LIMIT) -> str:
    text = (text or "").strip().replace("\n", " ")
    return text[:limit] + ("..." if len(text) > limit else "")


def _resolve_path(file_path: str) -> str:
    p = Path(file_path)

    if p.exists():
        return str(p.resolve())

    cwd_candidate = Path.cwd() / file_path
    if cwd_candidate.exists():
        return str(cwd_candidate.resolve())

    project_root = Path(__file__).resolve().parents[1]
    root_candidate = project_root / file_path

    if root_candidate.exists():
        return str(root_candidate.resolve())

    raise FileNotFoundError(f"File not found: {file_path}")


def _get_blocks(sections: list[dict]) -> list[dict]:
    return [
        block
        for section in sections
        for block in section.get("blocks", [])
        if block
    ]


def _get_code_blocks(sections: list[dict]) -> list[dict]:
    return [
        block
        for section in sections
        for block in section.get("blocks", [])
        if block.get("type") == "code"
    ]


def _relation_summary(block: dict) -> list[str]:
    rows = []

    for rel in block.get("relationships", []) or []:
        rows.append(
            f"{rel.get('type')} -> {rel.get('target_block_id')} "
            f"(confidence={rel.get('confidence')}, reason={rel.get('reason')})"
        )

    return rows


# --------------------------------------REPORTS-------------------------------------------

def report_file(file_path: str) -> dict:
    _divider(f"🔬 RELATIONSHIP DEBUG: {file_path}")

    path = _resolve_path(file_path)
    print(f"[INFO] File: {path}")

    docs = parse(path)

    if not docs:
        print("❌ No docs returned")
        return {"file": file_path, "ok": False}

    doc = docs[0]
    sections = (doc.metadata or {}).get("ast", [])

    blocks = _get_blocks(sections)
    code_blocks = _get_code_blocks(sections)

    function_counter = Counter(block.get("function") for block in blocks)
    type_counter = Counter(block.get("type") for block in blocks)

    print(f"[INFO] Sections   : {len(sections)}")
    print(f"[INFO] IR blocks  : {len(blocks)}")
    print(f"[INFO] Code blocks: {len(code_blocks)}")
    print(f"[INFO] Types      : {dict(type_counter)}")
    print(f"[INFO] Functions  : {dict(function_counter)}")

    _subdivider("ALL BLOCK IDS")

    for block in blocks:
        print(
            f"{block.get('id')} | "
            f"type={block.get('type')} | "
            f"function={block.get('function')} | "
            f"text={_preview(block.get('text', ''), 120)}"
        )

    _subdivider("CODE BLOCK RELATION CHECK")

    if not code_blocks:
        print("⚠ No code blocks found")
    else:
        for block in code_blocks:
            meta = block.get("meta", {}) or {}

            print("\n--- CODE IR BLOCK ---")
            print(f"ID                 : {block.get('id')}")
            print(f"Section ID         : {block.get('section_id')}")
            print(f"Block index        : {block.get('block_index')}")
            print(f"Function           : {block.get('function')}")
            print(f"Text               : {_preview(block.get('text', ''), 220)}")
            print(f"Parent instruction : {meta.get('parent_instruction')}")
            print(f"Parent ID          : {meta.get('parent_instruction_id')}")
            print(f"Relations          : {_relation_summary(block)}")

            print("\nEmbedding text:")
            print(block.get("embedding_text", ""))

    _subdivider("RELATION COUNTS")

    relation_counter = Counter()

    for block in blocks:
        for rel in block.get("relationships", []) or []:
            relation_counter[rel.get("type", "unknown")] += 1

    print(dict(relation_counter))

    missing_parent_code = [
        block
        for block in code_blocks
        if not (block.get("meta", {}) or {}).get("parent_instruction")
    ]

    if missing_parent_code:
        print("\n⚠ Code blocks missing parent instruction:")
        for block in missing_parent_code:
            print(f"- {block.get('id')} | {_preview(block.get('text', ''), 160)}")
    else:
        print("\n🟢 Every code block has a parent instruction.")

    return {
        "file": file_path,
        "ok": True,
        "blocks": len(blocks),
        "code_blocks": len(code_blocks),
        "missing_parent_code": len(missing_parent_code),
        "relations": dict(relation_counter),
    }


def report_summary(results: list[dict]) -> None:
    _divider("🏁 TWO-FILE RELATIONSHIP VERDICT")

    for result in results:
        if not result.get("ok"):
            print(f"❌ {result.get('file')} failed")
            continue

        print(
            f"{'🟢' if result['missing_parent_code'] == 0 else '🟡'} "
            f"{result['file']} | "
            f"blocks={result['blocks']} | "
            f"code={result['code_blocks']} | "
            f"missing_code_parent={result['missing_parent_code']} | "
            f"relations={result['relations']}"
        )

    total_missing = sum(r.get("missing_parent_code", 0) for r in results if r.get("ok"))

    if total_missing == 0:
        print("\n🟢 Relationship + embedding evidence check passed.")
    else:
        print("\n🟡 Some code blocks are not linked to parent instructions.")


# --------------------------------------ENTRY-------------------------------------------

def main() -> None:
    print("⚡ RELATIONSHIP DEBUG MODE\n")

    results = []

    for file_path in TEST_FILES:
        try:
            results.append(report_file(file_path))
        except Exception as exc:
            print(f"❌ Failed: {file_path} | {exc}")
            results.append({
                "file": file_path,
                "ok": False,
                "error": str(exc),
            })

    report_summary(results)


if __name__ == "__main__":
    main()