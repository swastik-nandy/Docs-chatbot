from typing import List, Dict, Any


def reciprocal_rank_fusion(
    vector_results: List[Dict[str, Any]],
    keyword_results: List[Dict[str, Any]],
    k: int = 60
) -> List[Dict[str, Any]]:

    fused: Dict[str, Dict[str, Any]] = {}

    # ---------------- INTENT DETECTION ---------------- #

    def is_command_query(results):
        # infer from vector (most reliable)
        command_hits = sum(1 for r in results[:5] if r.get("type") == "command")
        return command_hits >= 2

    command_mode = is_command_query(vector_results)

    # ---------------- FILTER BM25 (CRITICAL FIX) ---------------- #

    if command_mode:
        keyword_results = [
            r for r in keyword_results if r.get("type") == "command"
        ]

    # ---------------- HELPERS ---------------- #

    def add_result(result, weight):
        key = result.get("text")

        if key not in fused:
            fused[key] = result.copy()
            fused[key]["score"] = 0.0

        fused[key]["score"] += weight * float(result.get("score", 0.0))

    # ---------------- VECTOR (PRIMARY) ---------------- #

    for r in vector_results:
        add_result(r, 1.0)

    # ---------------- BM25 (FILTERED + WEAK) ---------------- #

    for r in keyword_results:
        add_result(r, 0.2)

    # ---------------- FINAL SORT ---------------- #

    results = list(fused.values())
    results.sort(key=lambda x: x["score"], reverse=True)

    return results