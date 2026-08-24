"""LLM client for answer composition.

Two implementations:
  - MockLLMClient: echoes retrieved context in a fixed template, no real
    language understanding, used when no API key is configured.
  - GeminiLLMClient: a temporary free-tier stand-in for local testing only.
    The project's intended production LLM is GPT-5-mini (OpenAI), per
    PROJECT_PLAN.md's cost/caching numbers; Gemini is NOT the target model,
    it's what's available to test the retrieval+guardrail pipeline against
    a real LLM before an OpenAI key exists. Swapping back to OpenAI later
    only means adding an OpenAILLMClient and changing get_llm_client()'s
    selection, callers (llm/pipeline.py) don't change.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import GEMINI_API_KEY, GEMINI_MODEL


class MockLLMClient:
    """Returns a plausible-shaped response so the rest of the pipeline
    (guardrail check, fallback logic) can be tested end-to-end. It does NOT
    simulate real language understanding, it just echoes back the retrieved
    context in a fixed template, real answer quality only exists once a
    real LLM API is wired in.
    """

    def generate(self, system_prompt, user_question, context_verses):
        if not context_verses:
            return None  # caller is responsible for the "not covered yet" fallback, not this mock

        verse = context_verses[0]
        return (
            f"(mock answer) Regarding your question, {verse['scripture']} {verse['chapter']}.{verse['verse_number']} "
            f"says: {verse['sanskrit_text']}"
        )


class GeminiLLMClient:
    """Temporary stand-in LLM for local testing, using the user's own free
    Gemini API key. Not the production model (see module docstring).
    """

    def __init__(self, api_key, model_name):
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model_name = model_name

    def generate(self, system_prompt, user_question, context_verses):
        if not context_verses:
            return None

        response = self._client.models.generate_content(
            model=self._model_name,
            contents=user_question,
            config={"system_instruction": system_prompt},
        )
        return response.text


def get_llm_client():
    if GEMINI_API_KEY:
        return GeminiLLMClient(GEMINI_API_KEY, GEMINI_MODEL)
    return MockLLMClient()
