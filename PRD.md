# AI Pandit — Product Requirements Document (PRD)

## 1. What we are building

An AI-powered spiritual companion app. Its core identity is a pandit who can answer, with full breadth, any question drawn from Hindu scripture, starting with the Bhagavad Gita and expanding to other texts over time. Every answer is grounded in a scholar-verified data layer (original Sanskrit verse, verified word meanings, sourced cross-references), never in an LLM's unverified general knowledge.

Beyond core Q&A, the product includes: voice interaction, Duolingo-style shloka pronunciation training, daily practice tracking, live-guided ritual sessions where the pandit walks the user through a ritual step by step and actually recites the mantras at the right moment (e.g. a full Diwali pooja, not just an explanation), panchang/muhurat lookup for auspicious timing, and eventually the AI pandit delivering its answers on video (an avatar speaking the response, not a separate content library). These are features and delivery modes layered on top of the core Q&A engine, not separate products.

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

### 5.5 Live-guided ritual sessions
- Not a static checklist, a live session: materials list shown upfront, then the pandit guides one step at a time, the user confirms each step is done (tap or spoken confirmation), and the pandit actually recites the associated mantra at that point, correctly pronounced, before moving to the next step.
- Regional/tradition variation notes where procedures genuinely differ, labeled rather than silently picking one.
- Scholar-verified per ritual as one complete, ordered unit, given the real-world stakes of a user performing physical actions based on the guidance.
- Camera-based automatic step detection (recognizing the user has completed a step without manual confirmation) is a deliberately deferred, separate later capability, not part of this feature's initial scope, see Section 8 and `PROJECT_PLAN.md` Phase 10 for why.

### 5.6 Panchang & muhurat
- Users can ask for the Hindu calendar (panchang) or auspicious timing (muhurat) for a date, festival, or ritual.
- Location-aware (sunrise/sunset and timezone affect the calculation) and honest about regional calendar convention differences (e.g. North vs South Indian systems can disagree on a festival's date), shown labeled rather than silently resolved.
- Sourced from an established astronomical/panchang calculation method, not the scripture lexicon, this is a calculation engine, not a retrieval task, and is held to its own accuracy standard (correct calculation method) rather than "matches a cited verse."

### 5.7 Expanded scripture coverage
- Additional texts (Upanishads, Puranas, etc.) added over time, each following the same verified-data process as the Gita, with an automated ingestion pipeline (PDF upload, extraction, automated error-flagging, scholar review) speeding up the mechanical work per text without weakening verification.

### 5.8 AI pandit on video (delivery mode, not a separate library)
- The same verified answers (Q&A, ritual guidance) delivered as video: an animated/avatar AI pandit speaking the response, with correct Sanskrit pronunciation, so the interaction feels like a present teacher rather than a chat log.
- Not a separate browsable content library, no new content is generated for video, the avatar speaks the same already-verified answer a user would otherwise get as text or audio.
- Users choose their preferred delivery mode: text, voice-only, or pandit-on-video.

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
- **Camera/privacy risk (Phase 10, deferred deliberately)**: camera-based ritual step detection introduces real-time probabilistic judgment (misreading a physical action) and camera access during a private religious moment. This is why it's scoped as a separate, later, explicitly-consented, fallback-always-available capability rather than bundled into the initial live-guided ritual feature.
- **Calculation-accuracy risk (panchang/muhurat)**: this data is calculated, not retrieved from scripture, so it needs its own accuracy validation against known reference panchangs, and regional convention differences must be labeled, not silently resolved, consistent with the non-denominational principle.
- **IP/content sourcing risk**: must use public-domain scripture text and properly licensed/cited scholarly sources, not scraped or copied translations/commentary that belong to others. Specifically: Monier-Williams licensing differs by exact CDSL release (some commercial-safe, some not), GRETIL licensing varies per text, and DCS tagging should be treated as a starting point for scholar review, not as ground truth on its own. Every source must be version-pinned and its license confirmed before commercial use.
- **Cost risk**: at meaningful scale (e.g. 10,000 monthly active users), LLM API cost could run from roughly $4,000/month (cheap model tier with prompt caching) to $30,000+/month (naive premium-model approach) for the same usage, model tier and caching strategy are a real cost lever, not a minor detail, and should be actively managed as usage grows.
- **Security-expectation risk**: no screen-capture prevention mechanism (on Android or iOS) is complete, a determined user can always bypass client-side protections. Product messaging must not imply otherwise.

See `PROJECT_PLAN.md` for the phased build plan and `architecture.md` for technical design, and `rules.md` for build constraints and AI behavior boundaries.
