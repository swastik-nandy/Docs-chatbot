def get_history_block(history: str) -> str:
    return f"""
---------------- CHAT CONTEXT ----------------
{history if history else "No prior conversation."}
"""