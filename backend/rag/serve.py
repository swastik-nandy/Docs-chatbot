from dataclasses import dataclass
from typing import Dict, Any, List
import os
import traceback

from dotenv import load_dotenv
load_dotenv()

# ---------------- STORE ---------------- #
from rag.ingestion.embeddings.store import QdrantStore

# ---------------- RETRIEVAL ---------------- #
from rag.retrieval.vector_search.cosine_similarity import VectorSearch
from rag.retrieval.keyword_search.bm25 import KeywordSearch
from rag.retrieval.fusion.hybrid import reciprocal_rank_fusion
from rag.retrieval.reranking.cross_encoder import CrossEncoderReranker

# ---------------- QUERY PROCESSOR ---------------- #
from rag.retrieval.query_processor.pipeline import process_query

# ---------------- LLM ---------------- #
from rag.generation.llm.orchestrator import LLMOrchestrator

# ---------------- CONVERSATION ---------------- #
from rag.conversation.manager import ConversationManager


# --------------------------------------HELPERS-------------------------------------------

def enrich_query_with_memory(query: str, conv: ConversationManager) -> str:
    """
    Inject relevant memory into query for better retrieval.
    """
    long_term = conv.get_long_term()
    recent = conv.get_recent()

    parts = [query]

    if long_term:
        parts.append(long_term[:150])

    if recent:
        for msg in reversed(recent):
            if msg["role"] == "user" and msg["content"] != query:
                parts.append(msg["content"])
                break

    return " ".join(parts)


def is_confirmation_query(q: str) -> bool:
    q = q.lower().strip()
    confirmations = [
        "are you sure",
        "you sure",
        "really",
        "sure?",
        "is that correct",
        "confirm that",
    ]
    return q in confirmations


def get_last_assistant_answer(conv: ConversationManager) -> str:
    for msg in reversed(conv.get_recent()):
        if msg["role"] == "assistant":
            return msg["content"]
    return ""


# --------------------------------------CHUNK MODEL-------------------------------------------

@dataclass
class Chunk:
    text: str
    heading: str
    context: str
    type: str
    metadata: Dict[str, Any]


# --------------------------------------FALLBACK-------------------------------------------

def fallback_response() -> str:
    return (
        "I couldn’t find a reliable answer for that in the documentation. "
        "Try asking something related to Next.js CLI or configuration."
    )


# --------------------------------------CLI-------------------------------------------

def run_cli():
    print("🚀 Starting RAG Assistant...\n")

    vector_size = int(os.getenv("EMBEDDING_DIMENSION", "768"))

    store = QdrantStore(vector_size=vector_size)
    raw = store.get_all()

    if not raw or not raw.get("payloads"):
        print("❌ No data found in vector store. Run ingestion first.\n")
        return

    chunks: List[Chunk] = [
        Chunk(
            text=p.get("text", ""),
            heading=p.get("heading", ""),
            context=p.get("context", ""),
            type=p.get("type", ""),
            metadata=p,
        )
        for p in raw["payloads"]
    ]

    vector = VectorSearch(store)
    bm25 = KeywordSearch(chunks)
    reranker = CrossEncoderReranker()

    try:
        llm = LLMOrchestrator()
    except Exception:
        print("\n🔥 LLM INIT FAILED:\n")
        traceback.print_exc()
        return

    conv = ConversationManager(max_turns=4)

    print("💬 Ready. Ask anything (type 'exit' to quit)\n")

    # ---------------- LOOP ---------------- #
    while True:
        q = input("> ").strip()

        if q.lower() == "exit":
            break

        debug = q.startswith("/debug")
        if debug:
            q = q.replace("/debug", "").strip()

        if not q:
            continue

        # ---------------- MEMORY (USER) ---------------- #
        conv.add_user(q)
        history_text = conv.get_formatted()

        # ---------------- 🧠 CONVERSATION SHORT-CIRCUIT ---------------- #
        if is_confirmation_query(q):
            last_answer = get_last_assistant_answer(conv)

            if last_answer:
                print("\n💡 Answer:\n")
                print(f"Yeah, that’s correct.\n\n{last_answer}")
                conv.add_assistant(last_answer)
                continue

        # ---------------- MEMORY → QUERY ---------------- #
        enriched_query = enrich_query_with_memory(q, conv)

        # ---------------- QUERY PROCESSING ---------------- #
        q_data = process_query(enriched_query)

        expanded_q = q_data.get("expanded", "")
        intent = q_data.get("intent")
        question_type = q_data.get("question_type", "default")

        if debug:
            print("\n🧠 QUERY ANALYSIS\n")
            print(f"Original       : {q}")
            print(f"Enriched       : {enriched_query}")
            print(f"Expanded       : {expanded_q}")
            print(f"Intent         : {intent}")
            print(f"Question Type  : {question_type}\n")

        # ---------------- GUARDRAILS ---------------- #
        if intent == "irrelevant":
            print("\n💡 Answer:\n")
            print("That seems outside the scope of the documentation.")
            continue

        if intent == "ambiguous":
            print("\n💡 Answer:\n")
            print("Your question is unclear. Try being more specific.")
            continue

        if intent == "meta":
            print("\n💡 Answer:\n")
            print("I’m a documentation assistant focused on Next.js and developer workflows.")
            continue

        # ---------------- RETRIEVAL ---------------- #
        try:
            vector_results = vector.search(expanded_q, top_k=12)
            keyword_results = bm25.search(expanded_q, top_k=12)

            fused = reciprocal_rank_fusion(vector_results, keyword_results)
            reranked = reranker.rerank(expanded_q, fused[:6])

        except Exception:
            print("\n🔥 RETRIEVAL ERROR:\n")
            traceback.print_exc()
            continue

        if debug:
            print("\n🔹 TOP RESULTS\n")
            for i, r in enumerate(reranked[:5], 1):
                print(f"{i}. {r.get('heading')} ({r.get('score', 0):.4f})")

        if not reranked or max(r.get("score", 0) for r in reranked) < 0.25:
            print("\n💡 Answer:\n")
            print(fallback_response())
            continue

        # ---------------- GENERATION ---------------- #
        try:
            answer = llm.run(
                query=expanded_q,
                results=reranked[:5],
                intent=intent,
                question_type=question_type,
                history=history_text
            )

            if not answer or answer.strip().lower() == "i don't know":
                print("\n💡 Answer:\n")
                print(fallback_response())
                continue

            print("\n💡 Answer:\n")
            print(answer)

            # ---------------- MEMORY (ASSISTANT) ---------------- #
            conv.add_assistant(answer)

        except Exception:
            print("\n🔥 FULL LLM ERROR TRACE:\n")
            traceback.print_exc()

            print("\n⚠️ FALLBACK RESULTS:\n")
            for i, r in enumerate(reranked[:3], 1):
                print(f"{i}. {r.get('heading')}")
                print(f"   {r.get('text', '')[:200]}...\n")


# --------------------------------------ENTRYPOINT-------------------------------------------

if __name__ == "__main__":
    run_cli()