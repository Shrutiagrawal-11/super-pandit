# AI Pandit — Project Plan

## The idea in one paragraph

An AI-powered spiritual companion for people who are curious about Hindu scripture but do not have the time, habit, or attention span to read the Vedas, Upanishads, Puranas, and Gita directly. Its core identity is a pandit who can answer, with full breadth, any question drawn from across the scriptures, not a narrow single-purpose app. Pronunciation training (Duolingo-style), daily practice tracking, and short-form video (Netflix-style) are additional features built around that core Q&A capability, not the main product. Its core promise is trust: every claim it makes is traceable to a real, verified scripture source, not generated from an LLM's unverified general knowledge of Sanskrit or Hindu tradition.

## The one rule that shapes every phase below

**No claim the pandit makes should be ungrounded.** Word meanings, grammar, names, stories, and rituals all come from a verified data layer built from established scholarship, not from an LLM's memory. The LLM's job is narrow: compose a clear, well-written answer from verified inputs. It never supplies its own Sanskrit interpretation. This is why the architecture is retrieval plus reasoning (RAG), not a custom-trained model, models can't be point-corrected the way a data layer can, and a scholar disagreeing with a claim should mean editing a record, not retraining a model.

## Where ML/DL actually belongs (and where it doesn't)

| Task | Approach | Why |
|---|---|---|
| Scripture knowledge, word meaning, names, stories | Verified data layer (lexicon + knowledge graph), not a trained model | Must be traceable, auditable, and instantly correctable by a scholar |
| Sanskrit grammar parsing (sandhi, compounds, case) | Sanskrit Heritage Engine / `sanskrit_parser`, self-hosted, rule-based | Deterministic, grounded in Panini's grammar; documented as the accuracy leader specifically on classical-register text like the Gita, not statistical guessing |
| Answer composition | GPT-5-mini (OpenAI), constrained to verified inputs only, with prompt caching | Cheap tier is sufficient since this is constrained composition, not open-ended reasoning; not the source of facts |
| Voice input/output | Speech-to-text / text-to-speech models | Legitimate, off-the-shelf DL use |
| Shloka pronunciation scoring | Fine-tuned acoustic model (wav2vec2-based or forced alignment) | The one place real training is justified, confirmed by research, no rule-based substitute exists for scoring spoken audio |
| Retrieval | Self-hosted embedding model (BGE-M3 or multilingual-E5-large) + PostgreSQL/pgvector | Off-the-shelf/self-hosted, not custom-trained; a light contrastive fine-tune of the embedding model specifically for Sanskrit-English retrieval is the one justified exception, since it's narrow, auditable, and revertible |

---

## Phase 0 — Verified Data Foundation (solo-founder stage, no team yet)

**Goal:** Prove the trust model works on a small, bounded slice of scripture, before any app exists.

- Pick one bounded starting text. Bhagavad Gita is the natural choice: ~700 verses, already has centuries of cross-referenced classical commentary (Shankaracharya, Ramanuja, Madhva) and heavy academic digitization.
- Gather from verified sources only: Monier-Williams Sanskrit-English Dictionary, Apte's dictionary, Digital Corpus of Sanskrit (DCS), GRETIL (source-tagged original texts), established commentaries. Licensing varies by exact source/version, pin the specific version used and confirm its license before any commercial use (see `rules.md` Section 7 for the specific caveats found, especially that Monier-Williams licensing differs between CDSL releases).
- Structure the data cleanly, per verse:
  - Original Sanskrit text (verbatim, sourced)
  - Grammatical breakdown (word split, case, root) — using Sanskrit Heritage Engine / DCS tooling, not guessed
  - Key term meanings **as they apply in that specific verse**, with source citation
  - Any name variants, etymological links, or connected stories, source-tagged
- Format it in a database-ready structure (e.g. structured JSON per verse) so it drops into the eventual database without rework.
- Recruit one scholar (even just one) to **review**, not create, this first slice.
- **Exit criteria:** one fully verified, scholar-reviewed dataset (e.g. full Bhagavad Gita) ready to be queried.

---

## Phase 1 — Core Retrieval + Reasoning Engine (MVP backend)

**Goal:** Build the pipeline that turns a verified dataset into trustworthy answers.

- PostgreSQL with the `pgvector` extension (HNSW index) for retrieval — embeds verses and their verified metadata, not raw internet text. One database instance, not a separate vector DB vendor; confirmed by real benchmarks to match or beat dedicated vector databases at this app's realistic scale (see `architecture.md` Section 5).
- The same Postgres instance holds the knowledge graph (entities/relations as edge tables, queried with recursive CTEs) for entities, names, cross-references, and stories from Phase 0. No separate graph database, benchmarked to be faster for this app's actual query shape (shallow fan-out, not deep pathfinding).
- Retrieval logic: given a user question, pull the small relevant slice (a handful of verses + their verified terms/links), never the whole corpus.
- LLM integration (GPT-5-mini, with prompt caching on the static system prompt) with strict prompting: compose an answer only from what was retrieved, always cite verse/source, never supply outside Sanskrit interpretation.
- Internal QA harness: a running set of test questions with known-correct, scholar-approved answers, run against the pipeline before every content or prompt change ships.
- **Cost target:** roughly $4,000-5,000/month in LLM API cost at 10,000 monthly active users asking ~5 questions/day, using the cheap-tier-plus-caching approach above (versus $30,000+/month on a naive premium-model, no-caching approach). Track actual cost against this target as usage grows.
- **Exit criteria:** you can ask a real question about the Gita and get a cited, verifiable answer, consistently, with no hallucinated citations, at the cost target above.

---

## Chatbot Specification (applies from Phase 1 onward)

This is the detailed behavior spec for the pandit chatbot itself, decided so it can be built consistently across text, voice, and eventually video.

### Scope
- MVP scope is the Bhagavad Gita only, but full-capability within that scope: meaning of a verse, context/background, cross-references to names or stories, practical application to a user's situation, comparisons between verses, all supported, not just simple lookup.
- Scope expands text-by-text in later phases (Phase 7), never capability-by-capability. The engine's behavior doesn't change as texts are added, only the verified dataset grows.

### Fallback behavior (no guessing, ever)
- If a question falls outside the verified dataset (a text not yet added, a claim with no scholar-verified source, an ambiguous/unresolvable case), the chatbot explicitly says it doesn't have a verified answer for that yet, rather than answering from general LLM knowledge.
- This applies even when the LLM "knows" a plausible answer. The constraint is enforced at the prompt/system level: the model is instructed to answer only from retrieved, verified context, and to say so plainly when nothing relevant was retrieved.
- The "I don't know yet" response should still be warm and in-persona, not a raw error message, e.g. acknowledging the question, explaining it's not covered yet, and inviting the user to ask about something within the Gita.

### Persona
- Warm, calm, teacher-like, patient. Speaks the way a good guide/teacher does: never condescending, never robotic, comfortable saying "here's what this verse says" rather than asserting personal opinions.
- Never claims to be a real human pandit or a religious authority; it presents itself as an AI guide grounded in verified scripture, honest about what it is.
- Consistent voice across text, voice, and later video narration, this should be written as a persona guide/style sheet that all future modalities draw from, not re-invented per feature.

### Answer format (every response)
1. Direct answer to the question, in plain, warm language.
2. The original Sanskrit verse(s) the answer is grounded in, shown verbatim.
3. Source citation (chapter and verse reference, e.g. Gita 2.47).
4. Brief context or explanation of key terms where relevant, using only scholar-verified meanings, never the LLM's own Sanskrit interpretation.
5. Optional gentle follow-up prompt (e.g. "would you like to know more about this idea elsewhere in the Gita?") to encourage continued exploration, not required on every turn.

### Guardrails
- Never fabricates a citation. If retrieval returns nothing relevant, no citation is shown, the fallback behavior above applies instead.
- Never asserts one sect's interpretation as the only truth, given the broad/non-denominational scope decision; where interpretations genuinely differ, says so.
- Does not give medical, legal, financial, or crisis-level personal advice framed as scripture guidance; redirects to appropriate real-world resources if a user's question suggests real distress.
- Every claim traceable to a specific verse and source, consistent with the project's core trust rule.

### Conversation memory
- Remembers context within a single conversation (so follow-up questions like "what about the next verse" work naturally).
- Does not need to build a long-term personal profile of the user at MVP stage, that consideration is deferred to Phase 5 (daily tracking), where remembering practice history becomes relevant.

---

## Phase 2 — MVP Product: Text Chat

**Goal:** Ship the smallest usable product to real users. This is the pandit as a full Q&A companion, not a single-feature app, scoped narrow in *content* (one text) but broad in *capability* (any question about that text).

- Mobile app shell (React Native/Expo, iOS/Android), chat interface. Includes proportionate screen-capture mitigation (`FLAG_SECURE` on Android, capture detection on iOS), with no claim of complete protection since none exists on either platform, see `architecture.md` Section 6.
- Text-based Q&A backed by Phase 1 engine, scoped to the Gita only (content scope, not capability scope, the same engine handles any type of question, meaning, context, cross-reference, application to daily life).
- Every answer shows the original Sanskrit verse, its source citation, and the composed explanation.
- Basic account system, no daily tracking, pronunciation training, or voice yet, those are separate features layered on top in later phases.
- Closed beta with a small user group to validate: do people trust it, do they come back, is the tone right for a "spiritual companion" versus a generic chatbot.
- **Exit criteria:** real users get accurate, cited answers to a wide range of question types and give qualitative feedback that the product feels trustworthy and useful.

---

## Phase 3 — Voice

**Goal:** Add voice as an input/output modality.

- Speech-to-text for spoken questions.
- Text-to-speech for spoken answers, ideally with a calm, appropriate voice persona.
- Correct Sanskrit pronunciation in generated audio (this needs real care, mispronounced Sanskrit undermines the whole trust premise).
- **Exit criteria:** a user can speak a question and hear a correctly-pronounced, cited answer.

---

## Phase 4 — Shloka Pronunciation Training (Duolingo-style, one feature among several)

**Goal:** Teach users to correctly pronounce shlokas, building daily habit.

- Curated set of shlokas with verified correct pronunciation (audio reference recordings, ideally scholar/pandit-recorded). The closest real-world precedent is Quranic recitation-scoring apps, which needed hundreds of hours of annotated reference audio for full production quality, an MVP scoped to Gita shlokas only can start meaningfully smaller, but budget real time for sourcing this audio, it is a genuine content task.
- Fine-tuned acoustic model (wav2vec2-based mispronunciation detection, or forced alignment via Montreal Forced Aligner) for pronunciation scoring, this is the one place training a model is genuinely the right call, confirmed by research, no rule-based substitute exists for scoring spoken audio.
- Gamified lesson structure: streaks, daily goals, progress levels.
- **Exit criteria:** users can practice a shloka and get meaningful, accurate feedback on their pronunciation.

---

## Phase 5 — Daily Practice & Tracking

**Goal:** Build the habit loop that brings users back daily.

- Daily shloka or reflection prompt.
- Streak tracking, reminders/notifications.
- Personal practice history (what they've learned, practiced, asked about).
- **Exit criteria:** meaningful daily active usage, not just one-time Q&A visits.

---

## Phase 6 — Live-Guided Ritual Sessions (e.g. Diwali Pooja)

**Goal:** Go beyond "explain the ritual" to an actual live session, the AI pandit walks the user through the pooja step by step, in real time, and recites the mantra at the right moment, the way a real pandit present in the room would.

- **Session structure**, paced by explicit user confirmation (tap or spoken "done"), not a static checklist read all at once:
  1. **Materials/items required**, shown upfront so the user can gather everything before starting (diya, cotton wicks, ghee, specific flowers, sweets, idols/images of the relevant deities).
  2. **Live, step-by-step guidance**: the pandit gives one instruction at a time ("light the diya with ghee"), the user performs it and confirms (tap "done," or says so via voice), the pandit then recites the associated mantra for that step, and moves to the next. This is a live guided session, not a document handed to the user beforehand.
  3. **Mantras/shlokas are actually recited by the pandit** at the correct point in the ritual (not just displayed as text), shown in Sanskrit with citation, same trust standard as core Q&A, correct pronunciation reusing the Phase 4 pronunciation work.
  4. **Regional/tradition variation notes**, where the procedure genuinely differs, labeled rather than silently picking one version.
- Requires explicit scholar sign-off per ritual, given the higher stakes of a user actually performing real, physical actions based on the app's guidance, not just reading an explanation. A ritual's step sequence and mantra placement is authored and reviewed as one complete, ordered unit, not assembled from fragments at answer time.
- **Explicitly deferred to a later phase, not part of this phase's scope**: automatic detection of what the user is physically doing via camera (e.g. recognizing the diya has been lit without the user confirming). This was considered directly and deliberately deferred: it is a genuinely different kind of system (real-time computer vision, not retrieval+composition), carries real accuracy risk in the middle of an actual ritual (a misread action could recite a mantra at the wrong moment, or fail to notice a completed step), and raises real camera-privacy considerations during a religious ritual in someone's home. Manual confirmation ships first because it is simpler, more reliable, and already delivers the core value (a live, paced, mantra-reciting session) without that risk. See Phase 10 for the camera-based extension.
- **Exit criteria:** a user can complete a full ritual (e.g. Diwali pooja) start to finish in a live session, guided one step at a time, with the pandit reciting each mantra at the correct moment, verified accurate by a scholar.

---

## Phase 7 — Ingestion Pipeline + Expand Corpus

**Goal:** Grow beyond the Gita into the broader scripture set, and build the tooling that makes adding each new text faster, without weakening the verification standard.

- Repeat the Phase 0 data process (gather from verified sources, structure, scholar review) for additional texts: Upanishads, Puranas, other core texts.
- Because the architecture never required retraining, this is purely a data-scaling phase, not an engineering rebuild.
- Expand the knowledge graph of entities/names/stories as more texts are added, so cross-referencing (the "why is this god called differently here" capability) grows richer over time.
- **Automated ingestion pipeline**, to reduce manual effort per new text, not to replace verification:
  1. **Upload**: a PDF (or other source document) is uploaded through an internal tool, not user-facing.
  2. **Prefer digital sources over scanning**: if a text already exists as clean digital text (GRETIL, DCS, Wikisource), use that instead of scanning a physical book, this avoids most extraction error before OCR is even involved.
  3. **Extraction**: direct text extraction for text-layer PDFs (near-zero error rate); for scanned pages, OCR specifically tuned for Devanagari, not a generic OCR default, which underperforms badly on Sanskrit's conjuncts and diacritics.
  4. **Automated cross-checking (the "minor mistakes only" mechanism)**: every extracted line is run through the Sanskrit grammar parser, a line that fails to produce a valid grammatical parse usually signals an extraction error, not unusual grammar, and gets flagged before a human ever sees it. Lines are also diffed against DCS/GRETIL where the verse likely already exists in a verified corpus, a near-match confirms the extraction; a mismatch becomes the specific, narrow thing a scholar is shown.
  5. **Cleaning and structuring**: automated splitting into verses, the grammatical breakdown from the check above, automated matching of terms against the existing verified lexicon where possible.
  6. **Staging, not live**: the structured output lands in a review queue with a confidence flag per line (derived from OCR confidence, parse success, and corpus-match result). Nothing from this pipeline enters the live, retrievable dataset automatically, this would defeat the entire trust architecture, an OCR error or an unverified passage could otherwise reach users as if it were scholar-approved.
  7. **Scholar review, prioritized by confidence**: a scholar reviews the staged content in the same review tool from Phase 0. The default view surfaces only the low-confidence-flagged lines for active attention; clean, high-confidence extractions are shown but pre-checked rather than requiring a full re-read, this is what actually gets the scholar to "checking minor mistakes" instead of re-verifying everything from scratch. The scholar approves, edits, or rejects, nothing is approved through inaction.
  8. **Auto-embed on approval**: once approved, embedding generation and the knowledge-graph link-up run automatically, no separate manual step needed here, this part is safe to fully automate since it operates only on already-verified content.
  - **What this pipeline removes**: manual retyping, manual sandhi-splitting, manual re-lookup of already-known terms, and, through confidence-flagging, most of the time spent re-checking lines that were already extracted correctly.
  - **What this pipeline deliberately does not remove**: the scholar's judgment call on accuracy. This is a speed improvement to Phase 0's process, not a bypass of it.
- **Exit criteria:** a second text (beyond the Gita) goes from PDF upload to fully live, scholar-approved, and embedded in under a defined target turnaround (e.g. days, not weeks, for a text of comparable length to the Gita), with broad scripture coverage building out across major texts over time, still fully sourced and cited.

---

## Phase 8 — AI Pandit on Video (video as a delivery mode, not a separate library)

**Goal:** Let the AI pandit deliver its answers as video, an animated/avatar pandit actually speaking the response, so the experience feels like talking with a present teacher rather than reading a chat log. This is not a separate "Netflix of shlokas" content library sitting alongside chat and voice, it's a third delivery mode for the exact same verified answers Phase 1-6 already produce.

- The underlying answer (text, Sanskrit verse, citation, or full ritual procedure from Phase 6) is exactly the same, generated by the same verified pipeline. Video changes only how it's delivered to the user: an avatar/animated AI pandit speaking the answer, with correct Sanskrit pronunciation (reusing the pronunciation work from Phase 4), rather than plain text or audio-only.
- No separate "video script written from scratch," the avatar speaks the already-composed, already-verified answer. Nothing new is generated for video that wasn't already scholar-approved through the standard pipeline.
- Users can choose their preferred delivery mode (text, voice-only, or pandit-on-video) per conversation or as a setting, this is a presentation layer choice, not a different product.
- Technically: this depends on a talking-avatar/video-generation approach (e.g. a pre-rendered pandit avatar driven by TTS + lip-sync, not a fully generative video model each time) and correct Sanskrit pronunciation in the avatar's speech, same trust bar as the voice feature in Phase 3.
- **Exit criteria:** a user can ask a question or request ritual guidance and receive the same verified answer delivered as a video of the AI pandit speaking it, correctly pronounced, with no divergence in content from the text/voice version of the same answer.

---

## Phase 10 — Camera-Based Ritual Step Detection (deferred extension of Phase 6)

**Goal:** Let the live-guided ritual session (Phase 6) recognize what the user is physically doing via camera, so the pandit can proceed automatically instead of requiring a manual "done" confirmation, once the manual-confirmation version has proven the core experience works.

- **Why this is its own phase, not part of Phase 6**: this is a genuinely different kind of system, real-time computer vision/action recognition, not retrieval-plus-composition, and it introduces a new category of risk the rest of this architecture was designed to avoid: a probabilistic, real-time judgment call happening in the middle of an actual religious ritual (misreading "diya lit" could recite a mantra too early, too late, or not at all). Shipping it separately means the proven, lower-risk manual-confirmation flow isn't blocked by, or complicated by, this harder problem.
- **Scope**: camera access (with clear, explicit user consent, and a clear choice to use manual confirmation instead at any time) to detect specific ritual actions (e.g. lighting a diya, holding an offering) and auto-advance the guided session.
- **Privacy-first by default**: video processing should be evaluated for on-device/local processing where feasible, rather than defaulting to streaming a live camera feed to a cloud service, given this happens during a private religious moment in someone's home. No video is stored beyond what's needed for the detection itself, this decision needs explicit review before shipping, it is not a minor implementation detail.
- **Fallback is always available**: if detection is uncertain or fails, the session falls back to manual confirmation rather than guessing, consistent with the project's core "never guess" rule, extended here from scripture claims to physical-action detection.
- **Exit criteria:** a user can optionally complete a guided ritual session with the pandit recognizing completed steps via camera, with manual confirmation always available as a fallback, and no action auto-advances on low-confidence detection.

---

## Phase 11 — Panchang & Muhurat

**Goal:** Let users ask for the Hindu calendar (panchang) and auspicious timing (muhurat) for a given date/event, e.g. "when is the muhurat for Diwali pooja this year," accurately and honestly about where calculations vary.

- **This is a different kind of data from scripture Q&A, and needs its own honest architecture**: panchang/muhurat aren't looked-up verified facts, they're *calculated* from astronomical positions (tithi, nakshatra, planetary positions, sunrise/sunset) for a specific date and location, using established astrological rules. There's no single verse to cite here, the correctness bar is "uses a correct, established calculation method," not "matches a verified text."
- **Location-aware**: sunrise/sunset and timezone genuinely change the calculation, use the user's location (with consent) rather than a generic default.
- **Convention differences labeled, not silently resolved**: regional calendar conventions (e.g. Amanta vs Purnimanta systems, North vs South Indian traditions) can genuinely disagree on which date a festival falls on. Consistent with this project's non-denominational principle, show the differing results labeled by convention (e.g. "North Indian calendar: [date], South Indian calendar: [date]") rather than picking one silently.
- **Data source**: a real, established panchang/astronomical calculation library or API (e.g. Swiss Ephemeris-based libraries, or an existing panchang API), reviewed for accuracy against known reference panchangs, not derived from the scripture lexicon/knowledge graph, this is a calculation engine integration, not a RAG retrieval task.
- Ties naturally into Phase 6 (live-guided rituals): a ritual session can reference the correct muhurat for that ritual on the user's actual date.
- **Exit criteria:** a user can ask for the panchang or muhurat for a specific date/festival/location and get an accurate answer, with regional convention differences clearly labeled where they exist.

---

## Phase 9 — Scale & Hardening

**Goal:** Handle real growth in users and content responsibly.

- Load testing and scaling of the retrieval/LLM pipeline (this was never the bottleneck by design, but validate under real traffic).
- Ongoing scholar review workflow as a standing process, not a one-time event, for corrections, new content, and disputed interpretations, tracked via the append-only audit log established in Phase 1 (see `architecture.md` Section 5).
- Monitoring for hallucination/drift: periodic re-running of the QA harness from Phase 1 as the LLM provider updates their models.
- Expanded team: at this point, a standing scholar board and a data/content pipeline role become justified, not before.

---

## Summary: what's actually hard here

The hard part of this product is not the AI engineering, retrieval and LLM composition are well-understood, off-the-shelf patterns. The hard part is the **verified data layer**: sourcing, structuring, and getting scholarly sign-off on scripture content, word meanings, and ritual procedures. Every phase above is sequenced so that engineering never gets ahead of verified content, and content work never has to wait on a model retrain to be corrected.
