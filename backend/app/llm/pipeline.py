"""End-to-end answer pipeline: retrieve approved verses, generate an answer
grounded in them, and reject anything that fails the citation guardrail
before it ever reaches a user (rules.md Section 4).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from llm.client import get_llm_client
from llm.prompts import SYSTEM_PROMPT, build_user_message
from llm.guardrails import passes_guardrail
from retrieval.search import search

FALLBACK_MESSAGE = (
    "I don't have a verified verse that directly answers this yet, so I don't "
    "want to guess. As more of the scripture is reviewed and added, I may be "
    "able to help with this in the future."
)


def answer_question(question, top_k=None):
    """Returns dict: answer, context_verses, grounded (bool)."""
    context_verses = search(question, top_k=top_k)

    if not context_verses:
        return {"answer": FALLBACK_MESSAGE, "context_verses": [], "grounded": False}

    client = get_llm_client()
    user_message = build_user_message(question, context_verses)
    raw_answer = client.generate(SYSTEM_PROMPT, user_message, context_verses)

    ok, reason = passes_guardrail(raw_answer, context_verses)
    if not ok:
        return {
            "answer": FALLBACK_MESSAGE,
            "context_verses": context_verses,
            "grounded": False,
            "rejected_reason": reason,
        }

    return {"answer": raw_answer, "context_verses": context_verses, "grounded": True}


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "What does Krishna say about duty?"
    result = answer_question(q)
    print(result["answer"])
    print(f"\ngrounded={result['grounded']}")
    for v in result["context_verses"]:
        print(f"  - {v['scripture']} {v['chapter']}.{v['verse_number']} (sim={v['similarity']:.3f})")
