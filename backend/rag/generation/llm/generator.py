#-----------------imports------------------------
from rag.generation.prompting.builder import build_prompt


#-----------------generator------------------------
class AnswerGenerator:
    def __init__(self, client):
        self.client = client

    def generate(
        self,
        query,
        results,
        intent,
        question_type,
        history,
        state="normal"
    ):
        """
        Generate final answer using LLM
        """

        #-----------------state conditioning------------------------

        # follow-up → make it conversational
        if state == "followup":
            query = f"Continue the previous explanation: {query}"

        # debug → sharpen query
        elif state == "debug":
            query = f"Help fix this issue: {query}"

        # explanatory → encourage depth
        elif state == "explanatory":
            query = f"Explain clearly: {query}"

        #-----------------build prompt------------------------
        prompt = build_prompt(
            query=query,
            results=results,
            intent=intent,
            question_type=question_type,
            history=history,
            state=state
        )

        #-----------------llm call------------------------
        response = self.client.generate(prompt)

        if not response:
            return None

        return response.strip()