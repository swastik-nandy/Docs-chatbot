#--------------------------------------MARKDOWN CLEANER-------------------------------------------

import re


def clean_markdown(text: str) -> str:
    """
    Clean markdown without destroying structure.

    KEEP:
    - headings (##)
    - tables (|)
    - lists (-, *)
    - paragraphs

    REMOVE:
    - images
    - excessive whitespace
    - noisy boilerplate lines
    """

    if not text:
        return ""

    #---------------- REMOVE IMAGES ----------------

    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)

    #---------------- SIMPLIFY LINKS ----------------
    # [text](url) → text
    
    text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)

    #---------------- REMOVE HTML TAGS (if any) ----------------

    text = re.sub(r"<[^>]+>", "", text)

    #---------------- REMOVE COMMON NOISE ----------------
    
    lines = text.split("\n")
    cleaned_lines = []

    NOISE_PREFIXES = (
        "**Applies to:**",
    )

    for line in lines:
        l = line.strip()

        if not l:
            cleaned_lines.append("")
            continue

        # drop noise lines
        if any(l.startswith(p) for p in NOISE_PREFIXES):
            continue

        cleaned_lines.append(l)

    text = "\n".join(cleaned_lines)

    #---------------- NORMALIZE NEWLINES ----------------
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()