from .client import LLMClient
from .rewriter import QueryRewriter
from .generator import AnswerGenerator
from .verifier import AnswerVerifier

from rag.generation.formatting.context_formatter import format_context


class LLMOrchestrator:
    def __init__(self):
        self.client = LLMClient()
        self.rewriter = QueryRewriter(self.client)
        self.generator = AnswerGenerator(self.client)
        self.verifier = AnswerVerifier(self.client)

    #-----------------run------------------------
    def run(self, query, results, intent, question_type, history, state="normal"):

        #-----------------rewrite------------------------
        try:
            rewritten = self.rewriter.rewrite(query, history)
        except Exception:
            rewritten = query

        #-----------------generate------------------------
        try:
            answer = self.generator.generate(
                query=rewritten,
                results=results,
                intent=intent,
                question_type=question_type,
                history=history,
                state=state   
            )
        except Exception as e:
            raise RuntimeError(f"GENERATION FAILED: {e}")

        #-----------------verify------------------------
        try:
            context = format_context(results)
            verified = self.verifier.verify(rewritten, answer, context)

            if verified and len(verified.strip()) > 3:
                return verified
        except Exception:
            pass

        return answer