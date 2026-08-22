# AI Pandit — Build Rules

Constraints for anyone (human or AI) building this project. These rules exist to protect the product's core promise: every answer is grounded in verified scripture, never in unverified AI guesswork.

## 1. Boundaries of the AI (non-negotiable)

- The LLM composes answers from retrieved, verified context only. It never supplies its own Sanskrit translation, word meaning, or interpretation from general training knowledge.
- If retrieval returns nothing relevant to a question, the app must say it doesn't have a verified answer yet. It must never let the LLM answer from general knowledge to "fill the gap."
- The LLM never fabricates a citation. A citation only appears if it's backed by an actual retrieved, verified source.
- The AI never claims to be a human, a religious authority, or a substitute for a real pandit where one is genuinely required (e.g. officiating a ceremony).
- The AI never asserts one sect/tradition's interpretation as the sole truth. Where traditions differ, it says so.
- The AI does not give medical, legal, financial, or crisis-level personal advice framed as scripture guidance. If a user's message suggests real distress, it responds with care and points to real-world resources rather than scripture alone.
- No feature ships that requires the app to assert something unverified, ever, even under deadline pressure. This is the one rule that overrides all others.

## 2. What to use

- **Backend language**: Python (FastAPI).
- **Frontend**: React Native (Expo), single codebase for iOS and Android.
- **LLM (composition only)**: GPT-5-mini (OpenAI), with prompt caching enabled on the static system prompt/persona block. Chosen specifically because this is a constrained composition task, not open-ended reasoning, a frontier-tier model buys nothing here and costs far more. Never used as a knowledge source.
- **Database**: PostgreSQL, single instance, serving relational data, the knowledge graph (edge tables + recursive CTEs), and vector search (via the `pgvector` extension with an HNSW index). Do not stand up Neo4j, Pinecone, Weaviate, or Qdrant at MVP-to-growth scale, real benchmarks show Postgres/pgvector matches or beats them at this app's realistic scale, and a second specialized database adds real operational cost (backup, monitoring, a second query language) with no corresponding benefit yet. See `architecture.md` Section 5 for the full reasoning; only revisit this if usage genuinely crosses the scale thresholds documented there.
- **Embeddings**: self-hosted open-weight multilingual embedding model (BGE-M3 or multilingual-E5-large), not a paid embedding API, this runs on CPU at near-zero marginal cost.
- **Sanskrit grammar parsing**: Sanskrit Heritage Engine / the `sanskrit_parser` Python package, self-hosted, rule-based, deterministic. This is the documented accuracy leader specifically on classical-register text like the Gita, not a custom-trained model. A neural fallback (e.g. ByT5-Sanskrit) may be used only when the rule-based parser finds no valid segmentation, never as the primary path.
- **Lexicon/word meanings**: scholar-curated dataset sourced from established academic references (Monier-Williams via a specific pinned CDSL version, Apte, DCS), never scraped from arbitrary websites. Confirm the license of the exact source version before use, see Section 7 below.
- **Audit logging**: a single append-only `content_audit_log` table populated via Postgres triggers (`old_values`/`new_values` as `jsonb`). Do not use event sourcing or a temporal-tables extension for this, both are unjustified complexity at this project's scale, see `architecture.md` Section 5 for why.
- **Mobile capture protection**: `react-native-capture-protection` is the only actively-maintained library in this space as of the last check; verify its maintenance status before adopting since this space has many abandoned libraries. `FLAG_SECURE` on Android is a real OS-level block; there is no equivalent true block on iOS, only after-the-fact detection. Never claim complete protection in user-facing copy, see Section 7 below and `architecture.md` Section 6.

## 3. What to avoid

- No fine-tuning or training a custom LLM on scripture content as a knowledge source. Corrections must be possible by editing verified data, not by retraining a model.
- No using an unverified translation or commentary as ground truth in the dataset. Only scholar-reviewed, source-cited material goes into the verified layer.
- No copying another author's specific translation or commentary text verbatim into the dataset without proper licensing, the underlying scripture is public domain, but a specific translator's wording may not be.
- No shipping a new ritual, verse set, or claim without it passing scholar review first.
- No silent fallback to "let the LLM just answer anyway" when verified data is missing, this must always be an explicit, visible product decision, never a quiet default.
- No storing sensitive user data (e.g. detailed personal distress disclosures) without clear necessity and proper security handling.
- No dark patterns in daily-streak/habit features (e.g. guilt-based notifications); the tone should stay consistent with a calm, respectful spiritual companion, not an engagement-maximizing growth app.

## 4. Error handling

- Every user-facing error (retrieval failure, LLM API failure, network issue) must degrade gracefully into the app's warm persona, never a raw stack trace or generic error code shown to the user.
- Distinguish clearly, internally, between three different "no answer" cases, and log them differently for review:
  1. No relevant data exists yet in the verified dataset (expected, becomes a content backlog signal).
  2. Retrieval or infra failure (a bug, should alert engineering).
  3. LLM output failed a guardrail check (e.g. attempted an uncited claim) and was blocked before reaching the user (should alert engineering and be reviewed, since it signals a prompt or pipeline issue).
- All LLM outputs pass through a post-generation check before being shown to the user: does every substantive claim map to something in the retrieved context? If not, the response is not shown as-is.
- Log enough detail (question, retrieved context, model output, guardrail result) to debug and improve the pipeline, while respecting user privacy.

## 5. Content and data integrity

- Every fact in the verified dataset must be traceable to a named source (text, edition, commentary, or academic reference).
- Corrections to verified data must be tracked with an audit trail: who changed what, from what, to what, when (see `architecture.md` for the specific mechanism).
- New texts, rituals, or major content additions require scholar sign-off before going live, not after.

## 6. Security and privacy defaults

- User conversation history and personal data are private by default, never used for marketing or shared with third parties without explicit consent.
- Follow platform-standard secure storage for any credentials, API keys, and tokens (never hardcoded, never committed to version control).
- Screen-capture protection is real but limited: `FLAG_SECURE` genuinely blocks screenshots/recording on Android; iOS has no true block, only detection-plus-blur. Neither stops a second-device photo, an accessibility-service reader, or a rooted/jailbroken bypass. Never state or imply complete protection in user-facing copy, this would itself be an ungrounded claim, which the whole product exists to avoid. See `architecture.md` Section 6 for the full detail.

## 7. Licensing checks before shipping

- Monier-Williams: license is version-dependent (current CDSL releases are CC BY-SA 4.0, commercial-safe with attribution; older mirrors are CC BY-NC-SA, non-commercial only). Pin the exact source/version used and confirm its license before any commercial release.
- Digital Corpus of Sanskrit (DCS): CC-BY, commercial-safe with attribution. Treat its tagging as a bootstrap corpus to be scholar-reviewed, not as ground truth on its own, since some tagging is heuristic rather than fully verified.
- GRETIL: licensing varies per text/contributor, do not treat it as blanket-clear, verify the license of each specific text used.
- Apte's dictionary: pre-1923 public-domain scans are safe; the CDSL structured non-commercial version is not, without separate licensing.
- Sanskrit Heritage Engine: CeCILL (copyleft), confirm whether calling it as an external service versus linking it directly into the codebase changes the obligations, before shipping.

## 8. Code discipline (for whoever, or whatever, is writing the code)

The person directing this build is not a coding expert and needs to be able to trust that code written on their behalf is honest, minimal, and correct, not just plausible-looking. This applies to AI-assisted code generation specifically.

- **Write the smallest amount of code that correctly solves the actual problem.** If a task needs roughly 10-20 lines, it should not become 150-200. Do not add abstractions, config options, helper layers, or "just in case" flexibility for needs that don't exist yet.
- **Prioritize correct logic over defensive bug-patching.** Think through the actual data flow and edge cases before writing code, rather than writing something plausible and then bolting on try/except blocks, null checks, and fallbacks to paper over cases that weren't reasoned through. A bug caught by a patch after the fact is a sign the logic wasn't understood first, not a sign the patch was good engineering.
- **No unexplained complexity.** If a piece of code isn't simple enough to explain in one or two plain sentences to someone non-technical, either the approach is wrong for this project's stage, or it needs a short comment explaining the non-obvious reason it exists (see `rules.md` general principle: comment the *why*, not the *what*).
- **No silent scope creep.** Don't refactor unrelated code, rename things, or "clean up while I'm here" during a task that didn't ask for it. Every change should be traceable to an actual request or an actual bug.
- **Flag uncertainty instead of guessing.** If a requirement is ambiguous or a technical approach has a real tradeoff, say so plainly and ask, rather than silently picking an approach and hoping it's what was wanted. This mirrors the product's own core rule (never guess, always be explicit about what's known versus not known), applied to the engineering process itself.
- **When something breaks, find why before writing more code.** Adding retries, broader exception handling, or extra validation without first identifying the root cause of a failure is not acceptable, it hides bugs rather than fixing them, and it's exactly the kind of code bloat this section exists to prevent.
