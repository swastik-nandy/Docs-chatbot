#-----------------client------------------------
import os
from groq import Groq


class LLMClient:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("Missing GROQ_API_KEY")

        self.client = Groq(api_key=api_key)
        self.model = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

    #-----------------new unified interface------------------------
    def generate(self, prompt: str, temperature: float = 0.6) -> str:
        """
        Simple generation interface (preferred)
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful, conversational developer assistant."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    },
                ],
                temperature=temperature,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            raise RuntimeError(f"LLM CALL FAILED: {e}")

    #-----------------optional legacy------------------------
    
    def chat(self, system: str, user: str, temperature: float = 0.6) -> str:
        """
        Lower-level interface (optional)
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            raise RuntimeError(f"LLM CALL FAILED: {e}")