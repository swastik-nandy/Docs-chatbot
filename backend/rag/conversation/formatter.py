from typing import List, Dict


class ConversationFormatter:

    @staticmethod
    def format(messages: List[Dict[str, str]], long_term: str = "") -> str:
        lines = []

        if long_term:
            lines.append("LONG TERM CONTEXT:")
            lines.append(long_term)
            lines.append("")

        if messages:
            lines.append("RECENT CONVERSATION:")
            for msg in messages:
                role = "User" if msg["role"] == "user" else "Assistant"
                lines.append(f"{role}: {msg['content']}")

        else:
            lines.append("No prior conversation.")

        return "\n".join(lines)