# --------------------------------------PROCEDURE HANDLER (GENERIC, STRUCTURE-ONLY)-------------------------------------------

from typing import List, Dict, Any

from rag.ingestion.chunking.engine.builders.chunk_builder import build_chunk
from rag.ingestion.chunking.utils import estimate_tokens


MIN_STEPS = 2
MAX_STEP_TOKENS = 180


def split(chunk, content: List[Dict[str, Any]]) -> List:

    if not content or not isinstance(content, list):
        return [chunk]

    steps = []
    current_step = None
    active_sequence = False

    for item in content:
        if not item:
            continue

        t = item.get("type")

        # ---------------- LIST ITEM → STEP ---------------- #

        if t == "list":
            items = item.get("items", []) or []

            if len(items) < 1:
                continue

            # start sequence
            active_sequence = True

            for v in items:
                text = str(v).strip()
                if not text:
                    continue

                if current_step:
                    steps.append(current_step)

                current_step = text

        # ---------------- ATTACHMENT ---------------- #

        elif t in {"code", "paragraph"} and active_sequence and current_step:

            text = (item.get("text") or "").strip()

            if text:
                # attach lightly (not blindly)
                if len(text.split()) < 40:
                    current_step += f"\n{text}"

        # ---------------- BREAK ---------------- #

        else:
            if current_step:
                steps.append(current_step)
                current_step = None

            active_sequence = False

    if current_step:
        steps.append(current_step)

    # ---------------- VALIDATION ---------------- #

    if len(steps) < MIN_STEPS:
        return [chunk]

    cleaned = [_clean(s) for s in steps if s]

    if len(cleaned) < MIN_STEPS:
        return [chunk]

    # ---------------- BUILD ---------------- #

    output = []

    for step in cleaned:
        tokens = estimate_tokens(step)

        if tokens <= 0:
            continue

        if tokens > MAX_STEP_TOKENS:
            continue

        output.append(
            build_chunk(
                original=chunk,
                text=step,
                subtype="procedure_step",
            )
        )

    return output if len(output) >= MIN_STEPS else [chunk]


# ---------------- CLEAN ---------------- #

def _clean(text: str) -> str:
    import re

    text = re.sub(r"^\s*[\-\*\u2022]\s*", "", text)
    text = re.sub(r"^\s*\d+[\.\)]\s*", "", text)

    return " ".join(text.split()).strip()