"""Post-generation faithfulness check, per rules.md Section 4: every LLM
output passes through this before being shown to a user. If a citation
appears in the answer that doesn't match anything actually retrieved, the
answer is rejected, never shown as-is.

This is a minimal, honest check: it verifies citations, not full semantic
faithfulness (that would need another LLM call to judge, real future work,
not something to fake with a naive check now).
"""
import re

CITATION_RE = re.compile(r"(\d+)\.(\d+)")


def extract_cited_verses(answer_text):
    """Returns a set of (chapter, verse) ints found in the answer text.
    A citation is only counted if immediately preceded by a scripture name
    at some point in the text — a bare "2.47" without "Gita" nearby isn't
    treated as a citation attempt, avoiding false positives on other numbers.
    """
    cited = set()
    for m in CITATION_RE.finditer(answer_text):
        window = answer_text[max(0, m.start() - 15) : m.start()]
        if "gita" in window.lower() or "gītā" in window.lower():
            cited.add((int(m.group(1)), int(m.group(2))))
    return cited


def passes_guardrail(answer_text, context_verses):
    """Returns (passes, reason). Fails if the answer cites any (chapter,
    verse) that wasn't actually in the retrieved context, that would be a
    fabricated citation, exactly what rules.md forbids.
    """
    if answer_text is None:
        return False, "no answer generated"

    cited = extract_cited_verses(answer_text)
    retrieved = {(v["chapter"], v["verse_number"]) for v in context_verses}

    fabricated = cited - retrieved
    if fabricated:
        return False, f"answer cited verse(s) not in retrieved context: {fabricated}"

    return True, None
