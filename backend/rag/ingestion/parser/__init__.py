# --------------------------------------PARSER ENTRY-------------------------------------------

import os

from .filetype import detect_type
from .markdown import load_markdown
from .cleaner import clean_markdown
from .ast_parser import parse_md_ast
from .adapters import normalize_mdx

# ENRICHER (modular pipeline)
from .enrichment.enricher import enrich


# --------------------------------------SUPPORTED TYPES-------------------------------------------

SUPPORTED_DOC_TYPES = {"markdown", "mdx"}


# --------------------------------------DOCUMENT MODEL-------------------------------------------

class Document:
    """
    Final parser output container.

    Keeps final text + structured AST together.
    """

    def __init__(self, text: str, metadata: dict):
        self.text = text
        self.metadata = metadata

    def __repr__(self):
        sections = len(self.metadata.get("ast", []))
        doc_type = self.metadata.get("doc_type", "unknown")
        return f"<Document type={doc_type} sections={sections}>"


# --------------------------------------HELPER LOG-------------------------------------------

def _log(stage: str, msg: str):
    print(f"[Parser::{stage}] {msg}")


# --------------------------------------MAIN PARSE-------------------------------------------

def parse(file_path: str):
    """
    End-to-end parsing pipeline.

    Supports:
        .md  -> markdown
        .mdx -> mdx

    Flow:
        file
        → detect type
        → load
        → optional MDX normalization
        → clean
        → AST
        → enrich
        → document
    """

    _log("START", file_path)

    if not os.path.exists(file_path):
        raise ValueError(f"File not found: {file_path}")

    # ---------------- FILETYPE ---------------- #

    doc_type = detect_type(file_path)
    _log("FILETYPE", doc_type)

    if doc_type not in SUPPORTED_DOC_TYPES:
        raise ValueError(f"Unsupported file type: {file_path}")

    # ---------------- LOAD ---------------- #

    raw_text = load_markdown(file_path)
    _log("LOAD", f"chars={len(raw_text)}")

    if not raw_text.strip():
        raise ValueError("Empty file content")

    # ---------------- MDX NORMALIZATION ---------------- #

    if doc_type == "mdx":
        raw_text = normalize_mdx(raw_text)
        _log("MDX_NORMALIZE", f"chars={len(raw_text)}")

    # ---------------- CLEAN ---------------- #

    clean_text = clean_markdown(raw_text)
    _log("CLEAN", f"chars={len(clean_text)}")

    if not clean_text.strip():
        raise ValueError("Empty content after cleaning")

    # ---------------- AST PARSE ---------------- #

    elements = parse_md_ast(clean_text)
    _log("AST", f"elements={len(elements)}")

    if not elements:
        raise ValueError("AST parsing failed")

    # ---------------- ENRICHMENT ---------------- #

    sections = enrich(elements)
    _log("ENRICH", f"sections={len(sections)}")

    if not sections:
        raise ValueError("Enrichment failed")

    # ---------------- BUILD DOCUMENT ---------------- #

    final_text = "\n\n".join(
        section.get("text", "")
        for section in sections
        if section.get("text")
    ).strip()

    document = Document(
        text=final_text,
        metadata={
            "source": os.path.abspath(file_path),
            "file_name": os.path.basename(file_path),
            "doc_type": doc_type,
            "ast": sections,
        },
    )

    _log("DONE", file_path)

    return [document]