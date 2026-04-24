def get_rules_block() -> str:
    return """
GROUNDING RULES:

- Prefer using the provided context when it is relevant and strong

- If context is weak, missing, or unrelated:
  → You are allowed to use your own knowledge to answer

- Do NOT hallucinate specific technical facts when context exists
- But you CAN:
  → explain concepts
  → answer general questions
  → provide background knowledge

- If unsure:
  → say it naturally
  → or ask a clarification

- The goal is to be helpful, not restricted
"""