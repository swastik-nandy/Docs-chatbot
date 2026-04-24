# --------------------------------------ANSWER VERIFIER (STRICT BUT NATURAL)-------------------------------------------

class AnswerVerifier:
    def __init__(self, client):
        self.client = client

    def verify(self, query: str, answer: str, context: str) -> str:

        # ---------------- EMPTY ---------------- #
        if not answer or len(answer.strip()) < 3:
            return answer

        # ---------------- PROMPT ---------------- #
        prompt = f"""
You are a careful answer reviewer.

Your job:
- Review the answer and improve it only when needed
- Keep the tone natural and human
- Distinguish between conversational replies and knowledge-grounded replies

You must apply these two modes:

1. CONVERSATIONAL / META MODE
Use this when the user's question is conversational, social, or about the assistant itself.
Examples:
- hi
- hello
- thanks
- who are you
- what can you do
- who you
- can you help me

Rules for this mode:
- The answer does NOT need documentation support
- Keep the answer natural, direct, and helpful
- Preserve good conversational answers
- Only fix wording if needed

2. KNOWLEDGE-GROUNDED MODE
Use this when the user's question is factual, technical, documentation-based, or depends on retrieved knowledge.

Rules for this mode:
- Use the provided information as the source of truth
- If the answer is fully supported, keep it or improve clarity
- If the answer is partially supported, remove or correct unsupported parts but keep the supported parts
- You may combine multiple pieces of provided information to form a complete answer
- Do NOT remove useful information just because it is not written word-for-word
- If the answer is genuinely not supported by the provided information, return exactly:
  "Apologies, but I don’t have enough information to answer that."

General rules:
- First decide whether the user's question is conversational/meta or knowledge-grounded
- Do NOT mention context or documentation
- Do NOT explain your reasoning
- Return ONLY the final answer

CONTEXT:
{context or "No useful retrieved information."}

QUESTION:
{query}

ANSWER:
{answer}

FINAL:
"""

        try:
            verified = self.client.chat(
                system="You verify answers carefully. Conversational replies may stand on their own, but factual technical replies must be grounded.",
                user=prompt,
                temperature=0.0,
            ).strip()

            # ---------------- SAFETY CHECK ---------------- #
            if not verified or len(verified.strip()) < 3:
                return answer

            verified_lower = verified.lower().strip()

            strict_fallbacks = [
                "apologies, but i don’t have enough information to answer that.",
                "apologies, but i don't have enough information to answer that.",
                "not enough information to answer that",
            ]

            if any(signal in verified_lower for signal in strict_fallbacks):
                return "Apologies, but I don’t have enough information to answer that."

            return verified

        except Exception:
            return answer