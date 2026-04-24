# --------------------------------------SMART CLI RERANKER (PRECISION-FIRST)-------------------------------------------

from typing import List, Dict, Optional
import re


CORE_COMMANDS = {"dev", "build", "start"}

TECHNICAL_HINTS = {
    "command", "commands", "cli", "flag", "flags", "option", "options",
    "parameter", "parameters", "port", "telemetry", "typegen", "build",
    "start", "dev", "upgrade", "https", "alias", "default",
}

BEHAVIORAL_HINTS = {
    "alias", "default", "without", "before", "after", "warning",
    "recommended", "optional", "required", "good", "know",
}

STOPWORDS = {
    "what", "is", "the", "when", "you", "run", "a", "an", "to", "do",
    "does", "of", "and", "in", "for", "on", "with", "without", "are",
}


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9_.-]+", (text or "").lower())


def _contains_phrase(text: str, phrases: List[str]) -> int:
    lowered = (text or "").lower()
    return sum(1 for p in phrases if p and p in lowered)


def _word_overlap_score(query_words: List[str], text: str) -> float:
    text_words = set(_tokenize(text))
    score = 0.0

    for word in query_words:
        if word in text_words:
            score += 0.12

    return score


def _is_behavioral_query(query_lower: str) -> bool:
    return any(w in query_lower for w in BEHAVIORAL_HINTS) or any(
        p in query_lower for p in [
            "without a command",
            "good to know",
            "what happens",
            "default port",
            "before ",
            "after ",
        ]
    )


def _is_list_query(query_lower: str) -> bool:
    return any(w in query_lower for w in ["list", "available", "all commands", "all options", "provide commands"])


def _is_command_query(query_lower: str) -> bool:
    return any(w in query_lower for w in ["command", "commands", "cli"])


def _is_flag_query(query_lower: str) -> bool:
    return any(w in query_lower for w in ["flag", "flags", "option", "options", "parameter", "parameters"])


def _is_main_query(query_lower: str) -> bool:
    return any(w in query_lower for w in ["main", "core", "basic", "primary"])


def rerank(query: str, results: List[Dict], q_data: Optional[Dict] = None) -> List[Dict]:
    query_lower = (query or "").lower().strip()
    q_data = q_data or {}

    raw_query_words = [w for w in _tokenize(query_lower) if w not in STOPWORDS]
    query_words = raw_query_words[:]

    is_priority = q_data.get("priority", False)
    is_debug = q_data.get("debug", False)
    vocab_expansions = q_data.get("vocab_expansions", []) or []
    entities = q_data.get("entities", []) or []
    intent = (q_data.get("intent") or "").lower().strip()

    is_command_query = _is_command_query(query_lower)
    is_flag_query = _is_flag_query(query_lower)
    is_main_query = _is_main_query(query_lower)
    is_behavioral_query = _is_behavioral_query(query_lower)
    is_list_query = _is_list_query(query_lower)

    for r in results:
        base = float(r.get("score", 0.0))

        heading = (r.get("heading") or "").lower()
        context = (r.get("context") or "").lower()
        text = (r.get("text") or "").lower()

        metadata = r.get("metadata", {}) or {}

        rtype = (r.get("type") or "").lower()
        subtype = (metadata.get("subtype") or "").lower()
        content_role = (metadata.get("content_role") or "").lower()
        command_context = (metadata.get("command_context") or "").lower()
        command_name = (metadata.get("command") or "").lower().strip()

        text_blob = " ".join([heading, context, text, command_context]).strip()
        boost = 0.0

        # ---------------- EXACT / PHRASE MATCH ---------------- #

        if query_lower and query_lower in text_blob:
            boost += 1.0

        exact_phrase_hits = _contains_phrase(
            text_blob,
            [
                "without a command",
                "good to know",
                "default port",
                "alias for",
                "before",
                "after",
            ],
        )

        boost += 0.35 * exact_phrase_hits

        # ---------------- RAW TOKEN MATCH ---------------- #

        boost += _word_overlap_score(query_words, heading) * 1.2
        boost += _word_overlap_score(query_words, context) * 0.8
        boost += _word_overlap_score(query_words, text) * 1.0
        boost += _word_overlap_score(query_words, command_context) * 1.0

        # ---------------- TYPE-AWARE PRIORS ---------------- #

        if is_command_query:
            if rtype == "command":
                boost += 0.65
            elif rtype == "flag":
                boost -= 0.25

        elif is_flag_query:
            if rtype == "flag":
                boost += 0.75
            elif rtype == "command":
                boost -= 0.15

        else:
            # neutral queries should not blindly favor command rows
            if rtype == "command":
                boost += 0.12
            elif rtype == "flag":
                boost += 0.05

        # ---------------- LIST / TABLE QUERIES ---------------- #

        if is_list_query:
            if content_role == "commands_table" or rtype == "command_list":
                boost += 0.9
            elif rtype == "command":
                boost += 0.35

        # ---------------- BEHAVIOR / NOTE QUERIES ---------------- #

        if is_behavioral_query:
            # favor explanatory/note-like chunks over raw command rows
            if subtype in {"note", "config", "concept"}:
                boost += 0.85
            if rtype in {"command_list", "command_options", "command_examples"}:
                boost += 0.45
            if rtype == "command":
                boost -= 0.15
            if rtype == "flag":
                boost -= 0.10

        # ---------------- CORE COMMAND LOGIC ---------------- #

        if is_command_query and command_name:
            if command_name in CORE_COMMANDS:
                boost += 0.35
            elif is_main_query:
                boost -= 0.35

        # ---------------- ENTITY ALIGNMENT ---------------- #

        if "command" in entities and rtype == "command":
            boost += 0.18

        if "flag" in entities and rtype == "flag":
            boost += 0.18

        if "port" in entities and "port" in text_blob:
            boost += 0.22

        # ---------------- VOCAB EXPANSION ALIGNMENT ---------------- #
        # Keep this weak so expansions do not overpower the raw question.

        for v in vocab_expansions:
            v = (v or "").lower().strip()
            if not v:
                continue
            if v in text_blob:
                boost += 0.08

        # ---------------- INTENT ALIGNMENT ---------------- #

        if intent == "action":
            if rtype in {"procedure", "command_examples", "command_options"}:
                boost += 0.25

        if intent == "definition":
            if subtype in {"note", "config", "concept"}:
                boost += 0.25
            if rtype in {"command_list", "command_options"}:
                boost += 0.18

        if intent == "explanation":
            if subtype in {"concept", "config", "note"}:
                boost += 0.22

        # ---------------- DEBUG BOOST ---------------- #

        if is_debug and any(w in text_blob for w in ["error", "fail", "issue", "debug"]):
            boost += 0.35

        # ---------------- PRIORITY BOOST ---------------- #

        if is_priority:
            if rtype == "command":
                boost += 0.20
            if content_role == "commands_table":
                boost += 0.15

        # ---------------- PENALIZE IRRELEVANT DENSE CHUNKS ---------------- #

        length = len(text_blob.split())

        if len(raw_query_words) >= 3 and _word_overlap_score(raw_query_words, text_blob) < 0.12:
            boost -= 0.25

        if length > 180 and subtype not in {"concept", "config", "note"}:
            boost -= 0.05

        # ---------------- FINAL ---------------- #

        r["score"] = base + boost

    return sorted(results, key=lambda x: x["score"], reverse=True)