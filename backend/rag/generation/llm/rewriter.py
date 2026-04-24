class QueryRewriter:
    def __init__(self, client):
        self.client = client

    def rewrite(self, query: str, history: str = None) -> str:

        if len(query.split()) >= 6:
            return query

        prompt = f"""
Rewrite the question into a clear standalone query.

RULES:
- Use chat history
- Resolve vague references
- Do NOT answer

CHAT HISTORY:
{history or "None"}

QUESTION:
{query}

REWRITTEN:
"""

        try:
            rewritten = self.client.chat(
                system="You rewrite queries.",
                user=prompt,
                temperature=0.0
            )

            return rewritten.strip() if rewritten else query

        except Exception:
            return query