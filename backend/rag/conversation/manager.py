from .memory import ConversationMemory
from .formatter import ConversationFormatter
from .long_term import LongTermMemory

from rag.generation.llm.client import LLMClient


class ConversationManager:

    def __init__(self, max_turns: int = 4):
        self.memory = ConversationMemory(max_turns)
        self.client = LLMClient()
        self.long_term = LongTermMemory(self.client)

    # ---------------- ADD ---------------- #

    def add_user(self, text: str):
        self.memory.add("user", text)

    def add_assistant(self, text: str):
        self.memory.add("assistant", text)
        self._maybe_update_long_term()

    # ---------------- LONG-TERM UPDATE ---------------- #

    def _maybe_update_long_term(self):
        messages = self.memory.get()

        # every 2 full turns (user + assistant = 4 messages)
        if len(messages) >= 4 and len(messages) % 4 == 0:
            chunk = ConversationFormatter.format(messages)
            self.long_term.update(chunk)

    # ---------------- ACCESS ---------------- #

    def get_recent(self):
        return self.memory.get()

    def get_long_term(self):
        return self.long_term.get()

    def get_formatted(self) -> str:
        """
        Returns fully formatted conversation context
        (long-term + recent memory)
        """

        return ConversationFormatter.format(
            messages=self.memory.get(),
            long_term=self.long_term.get()
        )

    # ---------------- UTIL ---------------- #

    def clear(self):
        self.memory.clear()