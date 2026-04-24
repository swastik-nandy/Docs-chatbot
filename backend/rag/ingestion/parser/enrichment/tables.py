#--------------------------------------TABLE ENRICHER-------------------------------------------

import re
from typing import Dict, Any, List


def _normalize_header(text: str, index: int = 0) -> str:
    """
    Normalize header keys safely and generically.
    Falls back to column_N when header text is empty.
    """
    key = re.sub(r"\W+", "_", str(text).strip().lower()).strip("_")
    return key or f"column_{index + 1}"


def _clean_value(value: Any) -> str:
    """
    Normalize a cell value without changing meaning.
    """
    text = str(value) if value is not None else ""
    text = re.sub(r"\s+", " ", text.strip())
    return text


def _row_has_content(row: Dict[str, str]) -> bool:
    return any(str(v).strip() for v in row.values())


def _row_to_text(headers: List[str], row: Dict[str, str]) -> str:
    """
    Convert one row into a generic retrieval-friendly text line.

    Example:
    column_a: foo | column_b: bar
    """
    parts: List[str] = []

    for header in headers:
        value = _clean_value(row.get(header, ""))

        if not value:
            continue

        pretty_header = header.replace("_", " ").strip()
        parts.append(f"{pretty_header}: {value}")

    return " | ".join(parts).strip()


def _table_to_text(headers: List[str], rows: List[Dict[str, str]]) -> List[str]:
    """
    Convert table rows into flattened text lines.
    Preserves only meaningful rows.
    """
    lines: List[str] = []

    for row in rows:
        if not _row_has_content(row):
            continue

        line = _row_to_text(headers, row)
        if line:
            lines.append(line)

    return lines


def _normalize_rows(rows: List[Dict[str, Any]], headers: List[str]) -> List[Dict[str, str]]:
    """
    Normalize all row keys/values into a consistent shape.
    Preserves only the header-defined columns.
    """
    clean_rows: List[Dict[str, str]] = []

    for row in rows:
        normalized_row: Dict[str, str] = {}

        for i, header in enumerate(headers):
            normalized_row[header] = _clean_value(row.get(header, ""))

        clean_rows.append(normalized_row)

    return clean_rows


def _build_table_profile(
    headers: List[str],
    rows: List[Dict[str, str]],
    anomalies: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """
    Generic structural signals about the table.
    No domain-specific meaning.
    """
    row_count = len(rows)
    non_empty_rows = sum(1 for row in rows if _row_has_content(row))
    col_count = len(headers)

    filled_cells = 0
    total_cells = row_count * col_count if row_count and col_count else 0

    for row in rows:
        for header in headers:
            if _clean_value(row.get(header, "")):
                filled_cells += 1

    density = (filled_cells / total_cells) if total_cells else 0.0

    return {
        "row_count": row_count,
        "non_empty_row_count": non_empty_rows,
        "column_count": col_count,
        "filled_cell_count": filled_cells,
        "cell_density": round(density, 4),
        "has_anomalies": bool(anomalies),
        "anomaly_count": len(anomalies or []),
    }


def enrich_tables(content: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enhance parsed tables without assuming domain semantics.

    Principles:
    - preserve parser output
    - preserve anomalies / raw signals
    - generate generic row-level text for retrieval
    - avoid hardcoded table types based on specific words
    """

    new_content: List[Dict[str, Any]] = []

    for item in content:
        if item.get("type") != "table":
            new_content.append(item)
            continue

        raw_headers = item.get("headers", []) or []
        raw_rows = item.get("rows", []) or []
        raw_row_backup = item.get("raw_rows", []) or []
        anomalies = item.get("anomalies", []) or []
        shape = item.get("shape", {}) or {}

        # Preserve even degraded tables
        if not raw_headers:
            raw_headers = []

        headers = [
            _normalize_header(header, index=i)
            for i, header in enumerate(raw_headers)
        ]

        if not headers and raw_rows:
            # derive fallback headers from widest row if possible
            widest = max((len(row) for row in raw_rows if isinstance(row, dict)), default=0)
            headers = [f"column_{i + 1}" for i in range(widest)]

        clean_rows = _normalize_rows(raw_rows, headers) if headers else []
        row_texts = _table_to_text(headers, clean_rows) if headers else []

        enriched = {
            **item,
            "type": "generic_table",
            "headers": headers,
            "rows": clean_rows,
            "row_text": row_texts,
            "text": "\n".join(row_texts).strip(),
            "table_profile": _build_table_profile(headers, clean_rows, anomalies),
        }

        # Preserve parser-level structural signals
        if raw_row_backup:
            enriched["raw_rows"] = raw_row_backup

        if anomalies:
            enriched["anomalies"] = anomalies

        if shape:
            enriched["shape"] = shape

        new_content.append(enriched)

    return new_content