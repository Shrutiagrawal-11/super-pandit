# Pending — Things On Shruti's Side

This is a running list of what's waiting on you specifically, not on more code. Update it as items get done or new ones come up. For "how do I actually do X," see `OPERATIONS.md`.

---

## 1. Scholar review — real current numbers (checked directly, not estimated)

| Scripture | Approved | Pending |
|---|---|---|
| Bhagavad Gita | 87 | 613 |
| Isha Upanishad | 0 | 18 |
| Vishnu Sahasranama | 0 | 142 |

- **What**: get the scholar to keep reviewing pending verses via the review tool (see `OPERATIONS.md` for how to open it).
- **Why it matters**: nothing unapproved is ever retrievable by the app. More approved verses = more the chatbot can actually answer.
- **Note for the scholar**: Gita chapter 13's verse count (34 vs 35) is a genuine edition difference, not an error — flagged in the `sources` table, the scholar can decide which convention to follow.
- **Isha Upanishad and Vishnu Sahasranama are already fully extracted and sitting in the database** (18 and 142 verses respectively) — they just need scholar review, same as the Gita. Not "not yet run" — already run, just not yet reviewed.

## 2. Add more scripture data

- **What**: this is explicitly your job going forward, not something the assistant should wait on.
- **Already extracted and pending review** (see table above): Isha Upanishad, Vishnu Sahasranama.
- **Next scriptures discussed but not started**: Ramayana Balakanda (you named this as the third priority after Isha Upanishad and Vishnu Sahasranama), and eventually the wider canon (Vedas, Upanishads, Puranas, etc.) per `PROJECT_PLAN.md` Phase 7.
- **After adding data**: re-run embeddings (`backend/app/retrieval/embed.py`) — it only processes newly-approved verses, safe to re-run any time.

## 3. Sanskrit verse audio (Vāgdhenu)

- **What**: pre-render correct-pronunciation Sanskrit audio for every approved verse, using the open-source Vāgdhenu model, on your other machine with a real Nvidia GPU.
- **Status**: researched and confirmed viable, not yet run. Full step-by-step is in `OPERATIONS.md`.
- **When**: once enough verses are scholar-approved to be worth a batch — no need to wait for all 700.
- **Cost**: Vāgdhenu itself is free (open-source, Apache-2.0). Only cost is your own electricity/GPU time — no rental needed since you have the hardware. Reference point: ~3 hours for 764 verses on the developer's own hardware, ~2.5GB VRAM peak.
- **After rendering**: a Sanskrit-literate reviewer (the scholar) should listen through the output before it ships, same trust bar as the text itself.

## 4. Decide on real production LLM key

- **What**: Gemini is a free-tier stand-in for testing only. The original plan's production model is GPT-5-mini (OpenAI).
- **Status**: not yet switched. Gemini works but is slow (11-17 seconds per answer) — expected to improve with the real production model.
- **Action needed**: get an OpenAI API key when ready to move off the free-tier testing setup.

## 5. Voice (Phase 3) — code built, blocked on your GPU step + a dev build

- **Speech-to-text**: built, via `expo-speech-recognition` (wraps the phone's built-in recognizer). Mic button in ChatScreen fills the input and auto-asks.
- **English text-to-speech**: built, via `expo-speech`. Speaker icon on each pandit reply reads the plain-language answer aloud.
- **Sanskrit verse audio**: backend now serves `/verse_audio/{slug}.wav` and `/ask` tells the client whether verified audio exists for the cited verse (`audio_url`). The speaker icon plays that file when present — it never runs the Sanskrit line through generic TTS. **This is empty until you run the Vagdhenu render (item 3) and drop files into `backend/app/static/verse_audio/` using the naming convention in `verse_audio_path()` in `backend/app/retrieval/verse_audio.py`** (e.g. `bhagavad_gita_2_47.wav`). This same audio is reused for mantra recitation in Phase 6 rituals below, no separate render needed.
- **Important**: `expo-speech-recognition` is a native module — it will NOT work in Expo Go. You need a dev build (`npx expo run:ios` / `npx expo run:android`, or an EAS dev build) to test the mic button. Everything else (TTS, verse audio playback) works fine in Expo Go.

## 6. Decide when to build later phases

Not urgent, but worth deciding when you're ready to prioritize:
- Phase 7: Broader corpus expansion + automated ingestion pipeline
- Phase 8: Video (AI pandit avatar)
- Phase 9: Scale/hardening
- Phase 10: Camera-based ritual step detection (deliberately deferred, after Phase 6 proves out)
- Phase 11: Panchang/muhurat lookups

## 7. Real user testing

- **What**: Phase 2's actual exit criterion — real users try the chat product and give feedback on whether it feels trustworthy and useful.
- **Status**: not started. This is the one thing in Phase 2 that genuinely needs you (or real testers), not more code.

## 8. Test the current app build on your phone

- **What**: you explicitly said "no i don't wanna test rn" partway through this session — that's a deferred action, not a done one.
- **Status**: the backend and mobile app are built and verified via curl/compile checks, but nobody has actually opened the real app on a real phone since the last round of fixes (auth-loading race fix, real chapter data on Home, save/remove wiring, screen-capture protection, timeout error messages).
- **How**: see `OPERATIONS.md` Section 5 for the ngrok-tunnel setup your router's client-isolation requires.

## 9. Send the new app design

- **What**: you said "i will give you a new design of the app" — the current settled design (off-white base, one accent color for real state only) stays live until you send whatever you have in mind.
- **Status**: not yet received.

## 10. Full pooja guidance with camera vision — sequencing decision

- **What**: you specifically raised full live-guided pooja (e.g. a complete Bhagavat pooja) with OpenCV recognizing physical actions (diya lit, offering made) instead of manual step confirmation.
- **Status**: this is already correctly scoped in `PROJECT_PLAN.md` as two phases — Phase 6 (manual-confirmation guided ritual, ships first) and Phase 10 (camera-based auto-advance, deliberately separate given the real-time-CV risk and in-home camera-privacy considerations). Confirmed as sound thinking, not reworked.
- **Open decision**: *when* to actually start Phase 6 relative to everything else — this was raised but never settled, since the conversation moved to other priorities in the same session.

## 11. HinduAI competitive positioning — an open UX question

- **What**: when comparing against HinduAI (a similar-looking competitor), the real differentiator found was: they're explicitly "inspired by" scripture with no verified-citation guardrail, this product is "grounded in" scripture with a real guardrail that refuses to answer outside retrieved context.
- **Open question, not yet decided**: most users won't perceive that difference unless the app's own UI makes it legible somehow (a visible "verified" indicator, a citation-always-shown pattern, some explicit trust signal). This is a product/UX decision for later, not a coded feature yet.

## 13. Phase 4 (pronunciation training) — code built, blocked on real content + a trained model

- **What's built**: `pronunciation_lessons` / `pronunciation_attempts` tables (migration `006_pronunciation.sql`, not yet applied — run it the same way you ran the earlier migration files), `/pronunciation/lessons`, `/pronunciation/attempts`, `/pronunciation/history` endpoints, and a full mobile screen (lesson list, record-and-score flow, per-syllable feedback).
- **Scoring is a stub right now** (`backend/app/pronunciation/scorer.py`, `SCORER_VERSION = "stub-v0"`): it returns random correct/incorrect per syllable, just to keep the app usable end-to-end. Swap its body for a real wav2vec2/Montreal Forced Aligner model once trained, no other code needs to change.
- **What's actually needed from you, per PROJECT_PLAN.md Phase 4**:
  1. Source verified reference-pronunciation recordings (scholar/pandit-recorded) for whichever shlokas you want to teach first. Insert them into `pronunciation_lessons` with `reference_audio_url` and `status='approved'` once reviewed. Until a lesson has approved status, it won't show up in the app.
  2. Train (or otherwise obtain) the real scoring model, and swap it into `scorer.py`.
- **Every pronunciation attempt also counts toward the Phase 5 daily streak automatically** (logged as activity_type `pronunciation`), so no separate wiring needed between the two features.

## 15. Phase 6 (live-guided ritual sessions) — code built, blocked on ritual authoring + scholar sign-off

- **What's built**: `ritual_sessions` now has a real FK to `users` (migration `007_ritual_sessions_fk.sql`, not yet applied). Endpoints for listing approved rituals, viewing materials/prep upfront, starting a session, reading the current step, and confirming a step (advances exactly one step, no auto-advance). Mobile screen (`RitualGuideScreen`) walks: ritual list → materials checklist → live one-step-at-a-time session with a "done, next step" button and mantra recitation (reusing Phase 3 verse audio, falls back to nothing spoken if that verse's audio isn't rendered yet — it never runs Sanskrit through generic TTS). Session progress is stored server-side, so closing the app mid-ritual and reopening resumes at the right step.
- **What's actually needed from you, per PROJECT_PLAN.md Phase 6**: author and get scholar sign-off on actual ritual content. Nothing shows up in the app until a `rituals` row exists with `status='approved'`. A ritual's `procedure_steps` is authored as one complete ordered JSON array up front (each step optionally naming a `mantra_verse_id`) — see `OPERATIONS.md` for the exact insert format and an example.
- **Explicitly not built here, by design**: camera-based auto-advance (that's Phase 10, deliberately separate — see architecture.md 2.3d). This phase is manual "done" confirmation only.

## 14. Phase 5 (daily practice tracking) — fully built and usable right now

- **What's built**: streak calculation (`/practice/streak`, computed live from the append-only `practice_sessions` log, never stored/cached so it can't drift), a rotating daily reflection prompt (`/practice/today`, `/practice/log`), practice history (`/practice/history`), and a full mobile screen with a streak card, today's prompt with a "mark as reflected" button, and a scrollable history list. Linked from Home for signed-in users.
- **No content or model dependency here** — this phase works today with zero further input from you, since it just tracks what a signed-in user actually does in the app.
- **Not built (a deliberate cut, not an oversight)**: push notification reminders. PROJECT_PLAN.md mentions "reminders/notifications" for Phase 5; that needs a notification-service decision (Expo push tokens, a backend job to send them) that's a separate, larger piece of infrastructure — flag if you want this prioritized next.

## 16. Phase 7 (automated ingestion pipeline) — code built, mostly usable now

- **What was already there before this round**: the actual extraction/structuring/cross-check/scholar-review tool (`data_pipeline/review_ui/`) already existed and works, that's what you've been using for the Gita/Isha Upanishad/Vishnu Sahasranama. Phase 7 in `PROJECT_PLAN.md` is specifically about *automating the mechanical steps and confidence-flagging on top of that*, not building ingestion from scratch.
- **What's newly built**: a grammar-parse check (`backend/app/grammar/sandhi_parser.py`, using `sanskrit_parser`) run automatically on every extracted line during `/ingest`; a `review_priority` (`low`/`normal`/`high`) computed from grammar-parse success + cross-check agreement (`data_pipeline/ingestion/confidence_check.py`); the scholar review page now sorts high-priority (likely extraction errors or cross-check mismatches) to the top and lets you filter to just those, while still showing everything by default — nothing is hidden, per architecture.md's "shown but pre-checked, not hidden" rule. New DB columns via migration `008_ingestion_confidence.sql` (not yet applied).
- **`sanskrit_parser` needs to actually be installed and working** (`pip install sanskrit_parser` in the venv) for the grammar-parse signal to do anything — if it's not installed, `grammar_parse_ok` just stays NULL and priority falls back to cross-check status alone, it doesn't break anything either way.
- **Not built, a genuine content-sourcing task, not a code gap**: per-line OCR confidence isn't tracked yet, `pytesseract` can return per-word confidence scores but `extract.py` doesn't currently capture them. Low priority to add unless you're about to ingest a heavily-scanned (non-digital) source, since GRETIL/DCS-sourced text has no OCR step at all.
- **"Prefer digital sources over scanning" (architecture.md 2.5 step 2)**: this is a workflow decision for you when picking a next source, not something enforced in code.

## 17. Old, still-open item from an earlier session

- **What**: an 1880 Nawal Kishor Press Hindi Gita edition on Archive.org was found to have unusably corrupted OCR text; a re-OCR test with Tesseract's Sanskrit/Hindi trained data was started but never finished or reported on.
- **Status**: unresolved, not revisited in the most recent session. Worth deciding whether to pick this back up or use a different Hindi source entirely.
