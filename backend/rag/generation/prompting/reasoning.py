def get_reasoning_block() -> str:
    return """
REASONING STEPS (internal):
1. Identify ALL relevant sources, not just the top one
2. Extract key facts from multiple sources if available
3. Build a general understanding first
4. Then include specific details (flags, commands, etc.)
5. Ignore unrelated or conflicting information
6. Combine consistent facts into a coherent explanation
"""