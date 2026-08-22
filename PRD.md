# AI Pandit — Product Requirements Document (PRD)

## 1. What we are building

An AI-powered spiritual companion app. Its core identity is a pandit who can answer, with full breadth, any question drawn from Hindu scripture, starting with the Bhagavad Gita and expanding to other texts over time. Every answer is grounded in a scholar-verified data layer (original Sanskrit verse, verified word meanings, sourced cross-references), never in an LLM's unverified general knowledge.

Beyond core Q&A, the product includes: voice interaction, Duolingo-style shloka pronunciation training, daily practice tracking, ritual guidance (e.g. Diwali pooja), and eventually a short-form video content library. These are features layered on top of the core Q&A engine, not separate products.

## 2. Why this exists (the problem)

People are curious about Hindu scripture and want to live by it, but are distracted, time-poor, and unlikely to read the Vedas, Upanishads, Puranas, or Gita directly. Existing options are either: unreliable (random internet content, ungrounded chatbot answers) or inaccessible (reading dense original texts or scholarly translations). There's no trustworthy, fast, personal way to get real answers from scripture.

## 3. Target user

- Someone spiritually curious or devoted, but time-constrained and easily distracted.
- Not necessarily fluent in Sanskrit or trained in scriptural study.
- Wants quick, trustworthy answers to real questions ("what does the Gita say about facing failure," "how do I perform Diwali pooja correctly," "why is this god called by different names").
- Motivated by habit-forming spiritual practice (daily reflection, learning to chant correctly), not just one-off lookups.
- Values authenticity: wants to know an answer is *actually* from scripture, not a generic AI guess.

## 4. Core product principle

**No claim the pandit makes should be ungrounded.** Every answer is traceable to a specific verse and source. When something isn't covered by the verified dataset yet, the app says so plainly rather than guessing. This principle overrides feature velocity, no feature ships that requires the app to assert something unverified.

## 5. Features

### 5.1 Core Q&A (text chat) — MVP
- Ask any question about the Bhagavad Gita (meaning, context, application, cross-reference).
- Every answer includes: plain-language response, original Sanskrit verse, source citation (chapter:verse), verified explanation of key terms.
- Explicit "not covered yet" response when no verified data supports an answer.
- Warm, calm, teacher-like persona throughout.

### 5.2 Voice interaction
- Ask questions by speaking; hear answers spoken back.
- Correct Sanskrit pronunciation in generated audio output.

### 5.3 Shloka pronunciation training (Duolingo-style)
- Guided lessons teaching correct pronunciation of specific shlokas.
- Pronunciation scoring against a verified reference recording, using a fine-tuned acoustic model, this is the one component in the whole product where training a model is the right call, since no rule-based approach can score spoken audio.
- Gamified structure: streaks, levels, progress.

### 5.4 Daily practice tracking
- Daily shloka or reflection prompt.
- Streaks and reminders.
- Personal history of what the user has asked, learned, and practiced.

### 5.5 Ritual guidance
- Step-by-step guided procedures for rituals (e.g. Diwali pooja), scholar-verified, with explicit labeling of tradition/regional variant where procedures differ.

### 5.6 Expanded scripture coverage
- Additional texts (Upanishads, Puranas, etc.) added over time, each following the same verified-data process as the Gita.

### 5.7 Short-form video library
- Netflix-style short clips explaining verses, stories, or rituals, built from the same verified data layer, scholar-reviewed before publishing.

## 6. Explicitly out of scope (for now)

- Taking a denominational stance between Hindu sects/traditions (product is broad/non-denominational; where interpretations differ, the app says so rather than picking one).
- Answering questions outside the verified dataset's current coverage.
- Medical, legal, financial, or crisis-level personal advice framed as scripture guidance.
- Claiming to be a human religious authority or replacing a real pandit for rites requiring one (e.g. formally officiating a wedding).

## 7. Success criteria (MVP)

- A user can ask a real question about the Gita and get an accurate, cited, verifiable answer.
- Users report the app feels trustworthy, not like a "generic AI guessing about religion."
- No hallucinated citations or fabricated Sanskrit interpretations observed in QA testing or user reports.
- Early users return for more than a single session (signal that the product has retention potential beyond novelty).

## 8. Key risks

- **Trust risk**: any hallucinated or wrong answer undermines the entire premise of the product. Mitigated by the verified-data-only architecture and explicit fallback behavior.
- **Content risk**: religious content is sensitive; getting a ritual or interpretation wrong, or appearing to favor one tradition, can cause real harm/backlash. Mitigated by scholar review and non-denominational framing.
- **Data bottleneck risk**: the founder currently has no scholar team or dataset; everything depends on Phase 0 data work landing before any app value can be delivered.
- **IP/content sourcing risk**: must use public-domain scripture text and properly licensed/cited scholarly sources, not scraped or copied translations/commentary that belong to others. Specifically: Monier-Williams licensing differs by exact CDSL release (some commercial-safe, some not), GRETIL licensing varies per text, and DCS tagging should be treated as a starting point for scholar review, not as ground truth on its own. Every source must be version-pinned and its license confirmed before commercial use.
- **Cost risk**: at meaningful scale (e.g. 10,000 monthly active users), LLM API cost could run from roughly $4,000/month (cheap model tier with prompt caching) to $30,000+/month (naive premium-model approach) for the same usage, model tier and caching strategy are a real cost lever, not a minor detail, and should be actively managed as usage grows.
- **Security-expectation risk**: no screen-capture prevention mechanism (on Android or iOS) is complete, a determined user can always bypass client-side protections. Product messaging must not imply otherwise.

See `PROJECT_PLAN.md` for the phased build plan and `architecture.md` for technical design, and `rules.md` for build constraints and AI behavior boundaries.
