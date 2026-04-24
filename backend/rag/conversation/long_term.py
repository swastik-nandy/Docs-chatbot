class LongTermMemory:

    def __init__(self, llm_client):
        self.client = llm_client
        self.summary = ""

    def update(self, history_chunk: str):
        prompt = f"""
Update long-term memory summary.

Keep:
- user goal
- tools/frameworks
- ongoing task

Remove:
- greetings
- filler text

CURRENT SUMMARY:
{self.summary or "None"}

NEW CONVERSATION:
{history_chunk}

UPDATED SUMMARY:
"""

        try:
            self.summary = self.client.chat(
                system="You maintain concise conversation memory.",
                user=prompt,
                temperature=0.1
            )
        except Exception:
            pass

    def get(self):
        return self.summary or ""