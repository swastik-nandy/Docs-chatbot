def get_conversation_state(conv):
    recent = conv.get_recent()

    if not recent:
        return "new"

    last_user = ""
    for msg in reversed(recent):
        if msg["role"] == "user":
            last_user = msg["content"]
            break

    q = last_user.lower().strip()

    # ---------------- FOLLOW-UP SIGNALS ---------------- #
    followup_phrases = [
        # pronouns / references
        "it", "that", "they", "this", "those", "these",

        # continuation phrases
        "and", "also", "then", "next", "more", "again",
        "continue", "go on", "what else", "anything else",

        # clarification followups
        "what about", "how about", "what if", "what next",
        "and then", "so then", "after that",

        # short vague queries
        "why is that", "how so", "like what", "such as",
        "for example", "example?",

        # conversational fillers that imply continuation
        "ok and", "okay and", "alright and", "right and",
        "cool and", "got it and",

        # refinement
        "more details", "explain more", "tell me more",
        "can you expand", "expand on that",

        # referencing previous answer implicitly
        "in that case", "in this case", "based on that",
        "from that", "using that",

        # short follow-up forms
        "else", "more?", "and?", "then?",

        # implicit continuation questions
        "what else can", "what else do", "what else does",
        "what else should", "what else is there",

        # chaining intent
        "and how", "and why", "and when", "and where",

        # casual continuation
        "so?", "now what", "what now",

        # developer-style followups
        "what about performance",
        "what about optimization",
        "what about production",
        "what about deployment",
        "what about edge cases",

        # correction-style continuation
        "no i mean", "i mean", "i meant",
        "let me rephrase", "actually",

        # referencing earlier topic loosely
        "regarding that", "about that", "on that",
    ]

    # ---------------- EXPLANATORY SIGNALS ---------------- #
    explanatory_phrases = [
        "why", "how", "how does", "how do", "how is",
        "why does", "why do", "why is",

        "explain", "explain this", "explain that",
        "explain how", "explain why",

        "what is", "what are", "what does",
        "what happens", "what causes",

        "can you explain", "can you describe",
        "can you walk me through",

        "break down", "give overview",
        "in simple terms", "simplify",

        "how it works", "how this works",
        "working of", "mechanism of",

        "difference between", "compare",
        "what's the difference",

        "deep dive", "details about",
        "internals of", "architecture of",
    ]

    # ---------------- DEBUG SIGNALS ---------------- #
    debug_phrases = [
        "error", "fail", "failed", "failure",
        "not working", "doesn't work", "doesnt work",
        "isn't working", "isnt working",

        "bug", "issue", "problem", "broken",
        "crash", "crashed",

        "exception", "stack trace", "traceback",

        "fix", "solve", "resolve",
        "how to fix", "how to solve",

        "debug", "debugging",
        "why is this failing",

        "unexpected", "wrong output",
        "incorrect", "not correct",

        "timeout", "hang", "stuck",

        "cannot", "can't", "unable to",
        "won't run", "won't start",

        "compilation error", "build error",
        "runtime error", "syntax error",

        "module not found", "undefined",
        "null", "none",

        "segmentation fault", "memory leak",
    ]

    # ---------------- MATCHING ---------------- #

    # Debug has highest priority
    if any(x in q for x in debug_phrases):
        return "debug"

    # Follow-up detection (strong signal)
    if any(x in q for x in followup_phrases):
        return "followup"

    # Explanatory intent
    if any(x in q for x in explanatory_phrases):
        return "explanatory"

    return "normal"