# AI Pandit — Architecture

This document covers the complete technical design: app flow, system architecture, folder structure, tech stack, data/fine-tuning strategy, LLM cost strategy, database design, and mobile security limits. It implements the principles in `PRD.md` and `rules.md`, and the phases in `PROJECT_PLAN.md`.

---

## 1. Tech stack

| Layer | Choice | Why |
|---|---|---|
| Backend | Python (FastAPI) | Async-friendly, strong ecosystem for ML/NLP tooling, pairs naturally with the retrieval/LLM pipeline |
| Frontend | React Native (Expo) | Single codebase for iOS + Android, strong support for chat UI, audio record/playback (voice), video playback (later phase), large hiring pool |
| Primary database | PostgreSQL | One system handles relational data, the knowledge graph (edge tables), and vector search (via pgvector) — see Section 5 for why a second specialized DB isn't justified at this stage |
| Vector search | pgvector (Postgres extension) | Matches or beats dedicated vector DBs at this app's realistic scale (up to ~1M+ vectors); avoids running a second database system for an MVP-stage team |
| Embeddings | Self-hosted open-weight model (BGE-M3 or multilingual-E5-large, lightly fine-tuned — see Section 4) | Free to run beyond compute, and fine-tuning is justified here specifically (narrow, auditable, revertible) |
| LLM (composition only) | GPT-5-mini (OpenAI), with prompt caching | Cheapest tier that's sufficient for constrained composition-from-context; not a knowledge source, so frontier-tier reasoning isn't needed (see Section 3) |
| Sanskrit grammar parsing | Sanskrit Heritage Engine / `sanskrit_parser`, self-hosted | Rule-based, deterministic, auditable; the documented accuracy leader specifically on classical/epic-register text like the Gita |
| Pronunciation scoring (Phase 4) | Fine-tuned acoustic model (wav2vec2-based or forced alignment via Montreal Forced Aligner) | The one place a real trained model is justified, no rule-based substitute exists for scoring spoken audio |
| Audio (voice, Phase 3) | STT/TTS APIs or self-hosted equivalents | Off-the-shelf, not a scripture-knowledge concern |

---

## 2. Complete app flow

### 2.1 Text Q&A flow (core, MVP)
1. User types a question in the chat UI (React Native).
2. Request hits the FastAPI backend (`/chat` endpoint).
3. **Sanskrit-aware retrieval**: the question is embedded (self-hosted embedding model); pgvector performs similarity search over `verse_embeddings` to find the most relevant verses.
4. For each candidate verse, the backend pulls its linked verified terms (`lexicon_terms` via `term_verse_links`) and any linked knowledge-graph entities/stories (`entity_verse_links`).
5. If nothing relevant is found above a confidence threshold, skip to step 8 with an empty context (triggers the "not covered yet" fallback).
6. The assembled context (verse text, verified term meanings, linked entity/story data) is passed to the LLM along with a system prompt enforcing the chatbot spec (persona, format, "never supply your own Sanskrit interpretation," always cite).
7. The LLM composes the response: plain-language answer, Sanskrit verse, citation, verified term explanation.
8. **Post-generation guardrail check**: does every substantive claim in the output map to something in the retrieved context? If not, the response is discarded and the fallback ("I don't have a verified answer for that yet") is returned instead.
9. Response streams back to the client and renders in the chat UI, with conversation history stored for session-level follow-up context.

### 2.2 Voice flow (Phase 3)
Same as above, with STT converting spoken input to text before step 2, and TTS converting the final response to speech after step 9 (using verified pronunciation for Sanskrit terms).

### 2.3 Pronunciation training flow (Phase 4)
1. User selects a shloka lesson.
2. App plays a verified reference recording and displays the transliterated text.
3. User records their attempt.
4. Audio is sent to the pronunciation-scoring model (self-hosted, fine-tuned per Section 4).
5. Score and specific feedback (which syllables/phonemes were off) returned and displayed.
6. Progress/streak data updated in `practice_sessions`.

### 2.4 Scholar review flow (content pipeline, all phases)
1. New/candidate content (verses, term meanings, KG facts, ritual steps) is entered into a staging area via an internal review tool (not user-facing).
2. A scholar reviews and approves/edits/rejects.
3. Approved changes write to the live tables, with every change recorded in the audit log (Section 5).
4. Only approved, live data is ever eligible for retrieval.

### 2.5 Automated ingestion flow (Phase 7, for adding new scripture texts)

This automates the mechanical steps of adding a new text (extraction, cleaning, structuring), it does not automate verification. Verification stays a required human step, for the same reason nothing else in this architecture lets an unverified claim reach a user.

1. **Upload**: a source PDF is uploaded through an internal tool.
2. **Prefer digital sources over scanning where possible.** If the same text already exists as clean digital text (GRETIL, DCS, Wikisource, an official digital edition), the pipeline should use that instead of re-extracting from a scanned physical book, this alone avoids most extraction error before OCR is even involved. Scanning is the fallback path, not the default.
3. **Extraction**: `pdfplumber`/`PyMuPDF` for text-layer PDFs (near-zero error rate, since no OCR is involved); for scanned pages, an OCR engine specifically tuned for Devanagari (e.g. Tesseract with its `san`-trained data, or a cloud OCR API with Devanagari support), not a generic English-trained OCR default, which meaningfully underperforms on Sanskrit's conjunct consonants and diacritics. Per-line OCR confidence scores are retained.
4. **Automated cross-checking, the actual "minor mistakes only" mechanism**, run before anything reaches a human:
   - **Grammar-parse check**: run the extracted line through the Sanskrit Heritage Engine / `sanskrit_parser`. A line that fails to produce any valid sandhi-split is usually a sign the *extraction* is wrong (a misread character), not that the grammar is unusual, classical verses are grammatically well-formed by construction. A failed parse is flagged as likely-extraction-error and, where feasible, automatically re-run through OCR or queued for a second extraction pass before it's shown to a scholar at all.
   - **Cross-reference against DCS/GRETIL**: for verses likely to already exist in an established verified corpus, run an automated diff against that source. A near-exact match is strong confirmation and lowers the line's flagged-review priority; a mismatch becomes the specific, narrow thing a scholar is shown, not the whole verse.
   - Only lines that fail both checks, or that are genuinely new/unmatched content, get a high review-priority flag.
5. **Cleaning and structuring**: automated verse-boundary detection, grammatical breakdown from the check above reused directly (no separate parse step), automated fuzzy-matching of terms against the existing `lexicon_terms` table to pre-fill likely meanings for scholar confirmation, not to auto-approve them.
6. **Staging**: output writes to staging tables (e.g. `staged_verses`, `staged_terms`), structurally identical to the live schema in Section 5 but with a `status` field (`pending`/`approved`/`rejected`) and a `confidence_flag` (derived from OCR confidence, parse success, and corpus-match result) so review effort concentrates on what's actually uncertain.
7. **Scholar review, prioritized by confidence**: the review tool's default view surfaces only low-confidence-flagged lines for active review; high-confidence lines (clean text-layer extraction, successful grammar parse, matched against a verified corpus) are shown but pre-checked, not hidden, a scholar can still open and correct anything, but isn't required to re-read every line from scratch. Nothing defaults to "approved" through inaction, this changes what the scholar spends attention on, not whether review happens.
8. **Promotion + embedding**: on approval, a background job copies the record from staging to the live tables (recorded in `content_audit_log`), and automatically triggers embedding generation for the new verse via `scripts/embed_corpus.py`. This step is safe to fully automate since it only ever operates on already-scholar-approved content.

**What this genuinely removes from a founder's workload**: manual retyping of source text, manual sandhi-splitting, manual re-lookup of terms the lexicon already has answers for, and, with the confidence-flagging above, most of the time spent re-reading lines that were already extracted correctly.

**What it does not remove**: the judgment call on whether an extracted verse, a term meaning, or a cross-reference is actually correct. Automating that step would mean the app could present OCR errors or unverified interpretations as scholar-approved fact, which breaks the project's core trust principle. The confidence-flagging approach reduces *how much* a scholar has to check, by directing attention only to what's actually uncertain, it does not remove the requirement that a human confirms new content before it goes live.

---

## 3. LLM cost strategy

The composition LLM is the only per-request paid-API cost in this pipeline; every other component (embeddings, grammar parsing, vector search) runs on infrastructure you already pay for or free/open-source tooling. Findings from cost research:

- **Model tier**: this is a constrained composition task (compose from provided context, refuse to freelance), not open-ended reasoning. A frontier-tier model buys nothing here. **GPT-5-mini** (~$0.25/$2 per MTok) is sufficient for this task, chosen as the project's LLM provider.
- **Prompt caching**: the system prompt, persona instructions, and faithfulness constraints are static across every call, the textbook case for prompt caching. OpenAI applies automatic prompt caching on repeated prefixes at no code-change cost; confirm the current discount percentage against live OpenAI docs, as it has shifted over time.
- **Context minimization**: cap retrieved context to the top few relevant verses and their linked terms, not full commentary, this is the largest lever on cost since fresh (uncached) tokens are the expensive part.
- **Estimated cost** at 10,000 monthly active users x 5 questions/day (~1.5M queries/month): roughly **$4,000-$5,000/month** on GPT-5-mini with prompt caching, versus roughly **$30,000+/month** on a naive premium-model, no-caching approach. Self-hosted open-weight inference (e.g. Llama 3.1 8B via Groq/Fireworks) could bring this to roughly $200/month at the same volume, but adds real ops and quality-monitoring burden; the recommended path is to **start on the GPT-5-mini API for MVP, and revisit self-hosting once volume is proven and stable.**
- **Non-LLM costs kept near zero**: self-hosted embeddings (CPU-only, no per-call cost), pgvector riding on the existing Postgres instance (no separate vector DB bill), self-hosted Sanskrit Heritage Engine / `sanskrit_parser` (open source, free).

---

## 4. Data and fine-tuning strategy

The core content principle holds: **no fine-tuning of the composition LLM on scripture content.** Errors in a fine-tuned model can't be point-corrected by a scholar the way a data-layer edit can, and can't be traced to a source. This was validated by research, not just assumed. Two narrow, different components genuinely justify training:

1. **Retrieval embedding model.** Off-the-shelf multilingual embeddings are measurably weaker on Sanskrit-English cross-lingual retrieval than on typical multilingual pairs. A light contrastive fine-tune of an existing multilingual embedder (e.g. BGE-M3) on Sanskrit-English query-passage pairs improves retrieval ranking specifically, it doesn't generate scripture "knowledge," and is fully re-trainable/revertible if evaluation shows regressions. This is the strongest and safest fine-tuning case in the whole pipeline.

2. **Shloka pronunciation scoring (Phase 4).** This is a genuinely different problem, phoneme-level acoustic scoring has no rule-based substitute. The closest real-world precedent is Quranic recitation-scoring apps, which use wav2vec2-based mispronunciation detection trained on large annotated reference-reciter corpora (hundreds of hours at full production quality; an MVP scoped to Gita shlokas only could start meaningfully smaller). This requires sourcing reference recordings from trained reciters, a real content task, not a technical shortcut.

**Everything else stays rule-based + retrieval + verified data:**
- **Sanskrit grammar (sandhi-splitting, morphology)**: the Sanskrit Heritage Engine is rule-based, deterministic, auditable, and is the documented accuracy leader specifically on classical-register text like the Gita. Use it as the primary parser; a neural fallback (e.g. ByT5-Sanskrit) is reasonable only for the rare case where the rule-based parser finds no valid segmentation, never as the primary path.
- **Word meanings**: sourced from Digital Corpus of Sanskrit (DCS, CC-BY, self-hostable, but treat as a bootstrap corpus, not ground truth, since tagging is partly heuristic) and dictionaries, all scholar-reviewed before entering the verified dataset.

**Licensing, flagged for legal review before shipping commercially:**
- DCS: CC-BY, commercial-safe with attribution.
- Sanskrit Heritage Engine: CeCILL (copyleft) — confirm whether calling it as an external service versus linking it into the codebase changes obligations.
- GRETIL: licensing varies per text/contributor, don't treat as blanket-clear, verify per text used.
- Monier-Williams: version-dependent, current CDSL releases are CC BY-SA 4.0 (commercial-safe with attribution/share-alike), but older mirrors are CC BY-NC-SA (non-commercial only). **Pin the exact source/version used and confirm its license before shipping.**
- Apte's dictionary: public-domain scans (pre-1923) are safe to use; CDSL's structured non-commercial version is not, without separate licensing.

---

## 5. Database architecture

**One Postgres instance serves relational data, the knowledge graph, and vector search.** A dedicated graph database (Neo4j) or vector database (Pinecone/Weaviate/Qdrant) isn't justified at this app's realistic scale, and adding either would mean running a second specialized system for no corresponding benefit at MVP-to-growth size.

- **Knowledge graph**: modeled as an edge table in Postgres (`entities`, `entity_relations`), queried with recursive CTEs (a small closure/materialized-path table can be added later if story-arc membership queries get frequent, to avoid recomputing that traversal every time). This app's graph usage is shallow fan-out (verse to term to entity to related entities/stories, 1-3 hops) for assembling RAG context, not deep pathfinding or graph-algorithm analytics. A real benchmark at a comparable scale (43,234 entities / 134,741 edges, close to this app's realistic knowledge-graph size) found Postgres recursive CTEs beating Neo4j by 4-7x on exactly this fan-out/neighborhood-expansion query shape ("what relates to this entity"), while Neo4j only pulled ahead by 1-2 orders of magnitude on deep shortest-path/link-analysis queries, which this app doesn't need. Combined with Neo4j's real operational cost (managed tiers start around $65-150+/month and realistically run $1,000+/month at real usage, plus a second query language and a second system to back up and monitor), a second database isn't justified here. Revisit only if the product later needs genuine multi-hop pathfinding (e.g. "narrative parallels between story arcs several hops apart"), not before.
- **Vector search**: Postgres + pgvector with an **HNSW index** (not IVFFlat, HNSW needs no training step and handles incremental inserts better as scripture/commentary content keeps being added). Confirmed by real benchmarks, not just general reasoning: Supabase's published 1M-vector benchmark showed pgvector's HNSW delivering over 10x the throughput of Pinecone's comparable pods at lower cost, and a Timescale/pgvectorscale benchmark at 50M vectors (well past this app's likely scale) still showed Postgres beating Qdrant on aggregate throughput, with only single-query tail latency slightly favoring Qdrant. pgvector's HNSW support has been production-hardened since version 0.8.0 (Oct 2024), which added iterative index scans, directly relevant here since this app will filter retrieval by scripture/chapter/translator, not just do plain similarity search, plus quantization (`halfvec`/binary vectors) to shrink index size if the corpus grows large. Running it via **Supabase** (or self-managed Postgres) means embeddings, verse metadata, and citation data live in one schema and can be joined in a single query, rather than syncing state between a relational DB and a separate vector-DB vendor. Revisit a dedicated vector DB only past roughly 10M+ vectors, very high concurrent query throughput, or a genuine need for multi-region low-latency serving, none of which apply at this app's realistic scale for years.

### Schema shape

- `verses`: canonical Sanskrit text, source/chapter/verse reference. One row per verse.
- `verse_translations` / `commentaries`: verse_id FK, translator/commentator, language, text. Normalized out since multiple exist per verse.
- `lexicon_terms`: term, verified meaning, scholar_id, status. Joined via `term_verse_links` (many-to-many, since a term recurs across verses with a per-verse-verified meaning).
- `entities` and `entity_relations`: knowledge graph nodes and edges (subject_id, predicate, object_id). `entity_verse_links` ties entities to the verses/stories they appear in.
- `verse_embeddings`: verse_id FK, embedding vector, model_version. Denormalized alongside verses rather than separated out, since this is a read-heavy, low-write path.
- `users`: accounts.
- `practice_sessions` / `streaks`: user_id, date, activity_type, score. Append-friendly, indexed by user_id + date.
- `conversations` and `messages`: standard chat history shape. Denormalize which verses/terms were cited directly onto the message row, rather than re-joining at read time, since chat history is read far more often than written.

### Audit trail for scholar corrections

**Use a single append-only `content_audit_log` table, populated via Postgres triggers, not event sourcing and not a dedicated temporal-tables extension.** This was checked against real precedent, not just general reasoning:

- **Why not event sourcing**: multiple independent sources (including a direct treatment of this exact question) conclude that needing an audit trail is explicitly *not* sufficient justification for event sourcing. Event sourcing's real payoff, replayable state, multiple projections, complex evolving business rules, doesn't apply to a small number of read-heavy content tables with occasional scholarly corrections. It would add an event store and rebuild-from-events complexity for a payoff this project doesn't need.
- **Why not Postgres's dedicated temporal-tables extension**: it's effectively unmaintained (years without real development) and, critically, unsupported on most managed Postgres (RDS, Cloud SQL, Supabase), which is where a small team's database actually runs. A hand-rolled range-type history table avoids that dead-extension risk but adds real schema complexity to solve a problem this project doesn't have yet (full point-in-time reconstruction of an entire row). The stated requirement, who changed what field, from what to what, when, is a change feed, not a bitemporal reconstruction need.
- **Why not SCD Type 2 as a named pattern**: it's a data-warehouse/ETL idiom for dimension tables feeding analytical fact tables, not an established pattern for OLTP correction-tracking. Adapting it onto live `verses`/`lexicon_terms`/`entities` tables would mean every read on the hot RAG-query path needs an `is_current = true` filter, and every correction becomes an insert-plus-update instead of a clean append, added risk and complexity on the hot path for no benefit over a separate log table.

**The actual implementation**: one `content_audit_log` table (`table_name`, `record_id`, `changed_by` [scholar id], `changed_at`, `old_values`/`new_values` as `jsonb`, optional `reason`/`citation` text field for the scholar's justification), populated via an `AFTER UPDATE`/`AFTER DELETE` Postgres trigger so corrections made through any path (admin UI, script, future bulk-import tool) are captured uniformly, without coupling the audit log's schema to the app code. Using `jsonb` for old/new values means adding a field to `lexicon_terms` or `entities` later doesn't require an audit-table migration. This keeps the primary content tables simple, normalized, and fast for the read-heavy RAG path, no `is_current` filters, no range-type joins, while still giving full who/what/when/from-what/to-what traceability, satisfying the project's core trust requirement.

One lesson worth borrowing from Wikidata (the closest real-world analog: collaboratively edited "verified facts" with provenance): attach the source citation to the fact itself (a `source_citation`/`reviewed_by` field on the live row), not only in the audit log. Wikidata's own team is still working to close exactly this gap after the fact, better to design it in from day one.

Revisit event sourcing or a temporal-tables approach only if the product later needs true point-in-time reconstruction of the full knowledge-graph state (e.g. for reproducing exactly what a past RAG answer was grounded in) or a multi-step draft-to-approval review workflow where the *process* itself, not just the end value, needs to be modeled and replayed.

---

## 6. Mobile security: screen capture prevention (realistic limits)

Be honest with users and in product messaging about what this can and cannot achieve, overstating it would itself violate the project's trust principle.

- **Android**: `FLAG_SECURE` set on a window genuinely and reliably blocks screenshots, screen recording (including third-party recorder apps), non-secure external display mirroring/casting, and blanks the app's thumbnail in the recent-apps switcher, this is documented, real OS-level behavior, not a library trick. Real limitations: it's per-window/activity, so every screen showing sensitive content must apply it individually; it does **not** block accessibility-service-based capture (banking trojans exploit exactly this gap, reading the accessibility tree rather than the pixel buffer, which sidesteps `FLAG_SECURE` entirely); and it's bypassable on rooted devices via actively-maintained tools (e.g. Magisk/LSPosed modules built specifically to strip `FLAG_SECURE`).
- **iOS**: there is no true screenshot-blocking API, confirmed still true as of 2026, Apple's own developer forums repeatedly state there is no public API for this, and their stated rationale is that a hard block just pushes leaks to an undetectable second-camera photo instead. `UIScreen.capturedDidChangeNotification` (or `sceneCaptureState` on iOS 17+) only detects an active recording after it has started, reactive, not preventive; the standard response is blurring content or showing a warning once detected. A separate "secure text field" trick (re-parenting real content into a `UITextField`'s secure internal layer) can hide a view from capture and is used by some enterprise apps, but it is explicitly unofficial and undocumented, depends on private UIKit internals Apple can change without notice, and carries real App Store review risk, not something to treat as a system guarantee. The one real iOS-side capture block that exists is not app-level at all: Microsoft Intune's MDM/enterprise policy can block screen capture for corporate-managed apps, not something a consumer app can invoke on its own.
- **Library choice, if used**: of the React Native libraries in this space, most are stale or abandoned; `react-native-capture-protection` is the one showing genuine current maintenance (active commits, minimal open-issue backlog) and wraps `FLAG_SECURE` on Android plus the detection/secure-view approach on iOS. Treat any library as a thin wrapper around the same underlying platform truth above, not as adding new capability.
- **Hard ceiling, cannot be prevented on any platform or by any app**: photographing the screen with a second device or camera, OS-level accessibility/screen-reader capture, jailbreak/root bypass of any client-side flag, or external capture hardware (HDMI capture cards, defeated only by link-level HDCP encryption, not by anything at the app layer). Even Netflix's protection isn't a "screenshot prevention feature" at all, it works because on hardware-backed DRM (Widevine L1/FairPlay) devices, decrypted video frames go straight from decoder to display hardware and never touch the framebuffer a screenshot API reads from; on non-DRM-enforced devices/browsers (Widevine L3, most desktops) captures work normally. That's a fundamentally stronger, DRM-licensing-dependent mechanism, not something available to a typical app. Banking apps combine `FLAG_SECURE`/iOS-detection with jailbreak/root detection and server-side monitoring, but security researchers describe root/jailbreak detection alone as "a helper countermeasure" that provides little value by itself, real security comes from how the app *responds* (step-up auth, session termination), not from the detection existing.
- **Proportionality**: banking/DRM-tier effort (hardware DRM licensing, device attestation, server-side heartbeat monitoring) is disproportionate for this app, leaked scripture explanations are not equivalent to financial or licensed-video data. Reasonable, proportionate scope: `FLAG_SECURE` on Android, capture-detection-plus-blur on iOS, and clear internal acknowledgment that a determined user can always photograph a screen or use a rooted device. Do not build, or claim, a false sense of complete protection, this would itself be a form of the ungrounded claim the whole product is trying to avoid.

---

## 7. Folder / file structure

```
yantras/
  PROJECT_PLAN.md
  PRD.md
  architecture.md
  rules.md

  backend/
    app/
      main.py                     # FastAPI app entrypoint
      api/
        chat.py                   # /chat endpoint (core Q&A flow)
        voice.py                  # STT/TTS endpoints (Phase 3)
        pronunciation.py          # scoring endpoints (Phase 4)
        practice.py               # daily tracking/streaks (Phase 5)
      core/
        config.py                 # settings, API keys via env vars, never hardcoded
        security.py               # auth, request validation
      retrieval/
        embeddings.py             # embedding model wrapper (self-hosted)
        vector_search.py          # pgvector query logic
        context_assembly.py       # pulls verse + terms + KG data into one context object
      grammar/
        sandhi_parser.py          # Sanskrit Heritage Engine / sanskrit_parser integration
      llm/
        client.py                 # OpenAI API wrapper (GPT-5-mini), prompt caching config
        prompts.py                # system prompt, persona, chatbot spec enforcement
        guardrails.py             # post-generation faithfulness check
      db/
        models.py                 # SQLAlchemy models matching schema in Section 5
        migrations/                # Alembic migration scripts
        audit.py                  # audit log write helpers
      scholar_tools/
        review_api.py             # internal content review/approval endpoints, not user-facing
        ingestion_api.py          # Phase 7: upload endpoint + staging queue endpoints for the PDF ingestion pipeline
      pronunciation_model/
        train.py                  # fine-tuning script for pronunciation scoring model
        infer.py                  # scoring inference at request time
    tests/
    requirements.txt / pyproject.toml

  frontend/
    App.tsx
    src/
      screens/
        ChatScreen.tsx
        VoiceScreen.tsx
        PronunciationScreen.tsx
        PracticeTrackerScreen.tsx
        RitualGuideScreen.tsx
        VideoLibraryScreen.tsx      # Phase 8
      components/
        ChatBubble.tsx
        VerseCitationCard.tsx
        StreakTracker.tsx
      services/
        api.ts                     # backend API client
        secureScreen.ts            # FLAG_SECURE / capture-detection integration
      state/
        conversationStore.ts
        userStore.ts
    ios/                            # native config, FLAG_SECURE-equivalent iOS handling
    android/                        # native config, FLAG_SECURE implementation

  data_pipeline/
    ingestion/
      gita_source_loader.py        # loads verses from verified sources (GRETIL etc.)
      lexicon_loader.py            # loads/structures Monier-Williams, Apte, DCS entries
      pdf_extractor.py             # Phase 7: PDF text extraction (text-layer + Devanagari-tuned OCR fallback)
      verse_segmenter.py           # Phase 7: automated verse-boundary detection on extracted text
      term_matcher.py              # Phase 7: fuzzy-matches extracted terms against lexicon_terms for scholar confirmation
      confidence_check.py          # Phase 7: grammar-parse validation + DCS/GRETIL cross-reference, produces per-line confidence_flag
    staging/                        # candidate content awaiting scholar review (staged_verses, staged_terms)
    eval/
      qa_test_set.json              # known-correct, scholar-approved Q&A pairs (Phase 1 QA harness)
      run_eval.py

  scripts/
    embed_corpus.py                 # batch-embeds verses into verse_embeddings
    audit_report.py                 # generates audit trail reports for review
```

---

## 8. What this architecture deliberately does not include (yet)

- No dedicated vector database or graph database, Postgres/pgvector covers the realistic scale for the foreseeable roadmap (Section 5).
- No fine-tuning of the composition LLM on scripture content, ever, under the current architecture (Section 4).
- No claim of complete screen-capture prevention, only proportionate, honest mitigation (Section 6).
- No multi-region infrastructure, self-hosted open-weight LLM serving, or event-sourced audit architecture at MVP stage, all explicitly deferred until real usage data justifies the added complexity.
