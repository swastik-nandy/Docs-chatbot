from typing import List, Dict


class ConversationMemory:
    def __init__(self, max_turns: int = 4):
        self.messages: List[Dict[str, str]] = []
        self.max_turns = max_turns

    def add(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})
        self._trim()

    def get(self) -> List[Dict[str, str]]:
        return self.messages

    def clear(self):
        self.messages = []

    def _trim(self):
        self.messages = self.messages[-(self.max_turns * 2):]