# --------------------------------------FILE TYPE DETECTION-------------------------------------------

from pathlib import Path


SUPPORTED_TYPES = {
    ".md": "markdown",
    ".mdx": "mdx",
}


def detect_type(file_path: str) -> str:
    """
    Detect supported documentation file type.

    This parser only supports:
    - .md
    - .mdx

    Returns:
    - "markdown" for .md
    - "mdx" for .mdx
    - "unknown" otherwise
    """

    if not file_path:
        return "unknown"

    ext = Path(file_path).suffix.lower()

    return SUPPORTED_TYPES.get(ext, "unknown")