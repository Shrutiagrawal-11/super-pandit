# Operations Guide

Step-by-step for the things you'll actually do yourself: opening the scholar review page, adding new scripture data, running the app, checking on things, and the Vāgdhenu audio render. Written so you don't need to remember this conversation.

All commands assume you're in `/Users/shruti/Desktop/yantras/` unless noted.

---

## 1. Starting everything up (do this first, every time)

Three things need to be running: Docker (the database), the API server, and — only if you're testing on your phone — Expo.

```bash
# 1. Start Docker Desktop if it's not already running
open -a Docker
# wait ~10-20 seconds for it to fully start

# 2. Confirm the database container is up (it should auto-start with Docker)
docker ps
# you should see yantras-db-1 in the list. If not:
docker start yantras-db-1

# 3. Start the API server
cd backend/app
source ../../.venv/bin/activate
nohup uvicorn api.main:app --host 0.0.0.0 --port 8000 > /tmp/api_server.log 2>&1 &

# 4. Confirm it's working
curl http://localhost:8000/health
# should print: {"status":"ok"}
```

If you're **not** testing on your phone, stop here — the API server running is enough for any backend/data work.

If you **are** testing on your phone, you'll also need Expo + tunnels (see Section 5).

---

## 2. Opening the scholar review page

```bash
cd data_pipeline/review_ui
source ../../.venv/bin/activate
uvicorn app:app --port 8420
```

Then open in a browser: **http://localhost:8420/review**

(Not `http://localhost:8420/` — that's the PDF-upload page, a different tool.)

What the scholar does there:
- Verses show one at a time, in chapter/verse order, all still "pending."
- Use the chapter dropdown at the top to jump to a specific chapter.
- For each verse, pick exactly one: approve our text, approve a cross-check source's text (if one is shown), or type a corrected text, or mark "needs further review."
- Type a name in the "your name" box before submitting — every decision is logged with who made it.
- There's no bulk-approve button anymore (it was removed after an accidental mass-approval earlier) — every verse is a deliberate, individual decision.

## 3. Checking how many verses are approved right now

```bash
docker exec yantras-db-1 psql -U pandit -d ai_pandit -c "SELECT scripture, scholar_status, count(*) FROM verses GROUP BY scripture, scholar_status ORDER BY scripture, scholar_status;"
```

## 4. Adding a new scripture's data

This is the part that's explicitly yours going forward — the assistant's job is to keep the pipeline correct, not to wait on or gate this.

General flow for any new text:
1. **Write (or reuse) an extraction script** in `data_pipeline/ingestion/` that pulls the Sanskrit verse text from a real source (GRETIL is the primary one used so far) and inserts rows into the `verses` table with `scholar_status = 'pending'` (never anything else — nothing skips review).
2. **Cross-check it** against an independent source if one exists, using `data_pipeline/ingestion/compare.py`'s logic (see `crosscheck_versejson.py` for a working example).
3. **Run the scholar review tool** (Section 2) to get it approved verse by verse.
4. **Re-run embeddings** so approved verses become actually retrievable by the chatbot:

```bash
cd backend/app
source ../../.venv/bin/activate
python3 retrieval/embed.py
```

This only processes verses that are approved AND not already embedded — safe to run any time, as often as you like, it won't redo work.

Already-written extraction scripts, not yet run to completion:
- `data_pipeline/ingestion/isha_upanishad.py`
- `data_pipeline/ingestion/vishnu_sahasranama.py`

## 5. Testing the app on your phone

Your home Wi-Fi router has "client isolation" turned on (a common security setting), which blocks the phone and your Mac from talking to each other directly on the same network — so this setup goes through ngrok tunnels instead of plain LAN.

**One-time setup** (only needed once, already done as of this session):
- ngrok installed (`brew install ngrok`)
- Free ngrok account created, authtoken configured (`ngrok config add-authtoken <your token>` — you ran this yourself)
- `@expo/ngrok` npm package installed globally

**Every time you want to test:**

```bash
# Terminal 1: tunnel the API server (do this after starting the API server from Section 1)
ngrok http 8000
# note the https://something.ngrok-free.dev URL it prints
```

```bash
# Terminal 2: start Metro with a tunnel
cd mobile
npx expo start --tunnel
```

Then in Metro's output, find the tunnel URL (something like `exp://xxxx-anonymous-8081.exp.direct`). Open Expo Go on your phone and either scan the QR code, or if that fails (a plain terminal QR code doesn't always render clearly enough for the Camera app to read), tap **"Enter URL manually"** in Expo Go and type that URL in directly.

**Important**: if the API server's ngrok tunnel URL changes (it does, on free ngrok, every time you restart it), you need to update it in one place:

`mobile/src/api/client.js` — change the `API_BASE_URL` constant to the new tunnel URL, then restart Expo.

## 6. Checking backend logs / debugging

```bash
tail -50 /tmp/api_server.log
```

## 7. Stopping everything

```bash
pkill -f "uvicorn api.main"
pkill -f "expo start"
pkill -f "ngrok http"
```

(Docker/the database can stay running — no need to stop it.)

---

## 8. Applying a new database migration

Same pattern as every migration so far, run it straight with psql:

```bash
docker exec -i yantras-db-1 psql -U pandit -d ai_pandit < backend/app/db/migrations/006_pronunciation.sql
```

Do this once to pick up the Phase 4 pronunciation tables.

## 9. Adding a pronunciation lesson (Phase 4)

Once `006_pronunciation.sql` is applied and you have a reviewed reference recording for a verse:

1. Serve the recording as a static file (same pattern as verse audio, `backend/app/static/verse_audio/`, see Section 11 — you can add these under a `backend/app/static/pronunciation_reference/` folder and mount it in `main.py` the same way `verse_audio` is mounted, if you want the app to actually play it).
2. Insert the lesson:

```bash
docker exec yantras-db-1 psql -U pandit -d ai_pandit -c "
INSERT INTO pronunciation_lessons (verse_id, reference_audio_url, transliteration, status, reviewed_by)
VALUES (
  (SELECT id FROM verses WHERE scripture = 'Bhagavad Gita' AND chapter = 2 AND verse_number = 47),
  '/pronunciation_reference/gita_2_47.wav',
  'karmanyevadhikaraste ma phaleshu kadachana',
  'approved',
  'your name'
);
"
```

A lesson only shows up in the app once `status = 'approved'`.

## 10. Phase 5 (daily practice tracking)

Nothing to run, this works as soon as the API server is up. Streaks and history are computed live from the `practice_sessions` table (already existed in the schema, just unused until now). Pronunciation attempts (Phase 4) automatically log into the same streak.

---

## 11. Running the Vāgdhenu Sanskrit audio render (on your GPU machine)

Do this on your other machine (the one with the Nvidia GPU), not this Mac — Vāgdhenu needs CUDA, which Apple Silicon doesn't have.

**One-time setup:**

```bash
git clone https://github.com/prathoshap/vagdhenu
cd vagdhenu
bash scripts/setup.sh
```

This installs PyTorch with CUDA 12.1, all dependencies, BigVGAN, and downloads the model weights into `models/`. Needs Python 3.10 and a CUDA 12.1-compatible GPU. Peak VRAM usage is modest — about 2.5GB — so most real GPUs handle this fine.

**Building the input file** (a "shard" — one entry per verse-line):

Each entry looks like:
```json
{"id": "gita_2_47", "meter": "anushtubh", "padas": ["कर्मण्येवाधिकारस्ते मा फलेषु कदाचन"], "seed": 60, "out": "out/gita_2_47.wav"}
```

- `id`: any unique label
- `meter`: almost all Gita verses are `"anushtubh"` — a handful elsewhere in the canon may need a different meter name (ask if unsure, or check the syllable count against the supported meter list)
- `padas`: the actual Devanagari verse-line text — pull this straight from the `verses` table for approved rows
- `seed`: any number, keep it consistent for reproducibility
- `out`: where the output `.wav` file should be saved

Save a batch of these as a JSON array in one file, e.g. `gita_batch_1.json`.

**Running the render:**

```bash
python src/render.py --shard gita_batch_1.json --results /tmp/render_results.json --outdir out
```

Output `.wav` files land in the `out/` directory, one per verse.

**Before shipping any of it**: have the scholar (or anyone Sanskrit-literate) actually listen through the rendered audio and flag anything that sounds wrong, same review standard as the text itself. This is the whole point of pre-rendering instead of live TTS — it's actually possible to check.

---

## Quick reference: what each file/folder is

| Path | What it's for |
|---|---|
| `data_pipeline/ingestion/` | Scripts that pull scripture text from sources into the database |
| `data_pipeline/review_ui/` | The scholar review web tool |
| `backend/app/api/` | The real API server the mobile app talks to |
| `backend/app/retrieval/` | Embedding generation + vector search |
| `backend/app/llm/` | The LLM composition + citation guardrail |
| `mobile/` | The actual React Native/Expo app |
| `PENDING.md` | Running list of what's waiting on you |
| `chat-history.md` | Full narrative log of everything discussed and built |
