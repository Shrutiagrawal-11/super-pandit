"""Local review UI for the scripture ingestion pipeline.

Run: uvicorn app:app --reload --port 8420  (from data_pipeline/review_ui/)
Then open http://localhost:8420
"""
import re
import sys
import tempfile
from pathlib import Path

from fastapi import FastAPI, Request, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

sys.path.insert(0, str(Path(__file__).parent.parent / "ingestion"))
from extract import extract_pages
from structure import parse_verses
from compare import compare_verses
from write_db import write_comparison_results

import psycopg
from write_db import DSN


_DEVANAGARI_DIGITS = "०१२३४५६७८९"


def clean_for_storage(raw_text, verse_number):
    """A cross-check source's raw text (as scraped) often has multi-line
    layout, stray leading/trailing whitespace, and its own embedded verse-
    number marker in whatever digit/punctuation convention that source used
    (e.g. "1.12" in Western digits, "।।" instead of "॥"). When a scholar
    chooses to replace our stored text with a cross-check source's reading,
    it should go in clean and in OUR storage convention, not carry over that
    source's raw scraping artifacts: single-spaced, and ending in "॥ N ॥"
    with N as a Devanagari numeral, matching every other verse already in
    the database (see the sanskrit_text of any existing row).
    """
    text = re.sub(r"\s+", " ", raw_text.strip())
    # Strip whatever trailing verse-number marker the source used, e.g.
    # "।।1.12।।", "||12||", "॥ १२ ॥" (danda/pipe, digits, danda/pipe), then
    # rebuild it in our own convention below rather than trying to normalize
    # every source's punctuation/digit choice in place.
    text = re.sub(r"[।॥|]+\s*[०-९\d]+(?:[.\-][०-९\d]+)?\s*[।॥|]*\s*$", "", text).strip()
    devanagari_number = "".join(_DEVANAGARI_DIGITS[int(d)] for d in str(verse_number))
    return f"{text} ॥ {devanagari_number} ॥"

app = FastAPI()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

_last_comparison = {}  # in-memory holding area for the just-run comparison, single-user local tool


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {})


@app.post("/ingest", response_class=HTMLResponse)
async def ingest(
    request: Request,
    scripture_name: str = Form(...),
    primary_title: str = Form(...),
    primary_pdf: UploadFile = None,
    check1_title: str = Form(""),
    check1_pdf: UploadFile = None,
    check2_title: str = Form(""),
    check2_pdf: UploadFile = None,
):
    def save_and_parse(upload):
        if upload is None or not upload.filename:
            return None
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(upload.file.read())
            path = tmp.name
        pages, method = extract_pages(path)
        records, warnings = parse_verses(pages)
        return {"records": records, "warnings": warnings, "method": method}

    primary = save_and_parse(primary_pdf)
    if primary is None or not primary["records"]:
        return templates.TemplateResponse(request, "index.html", {
            "error": "Could not extract any verses from the primary PDF. "
                     f"Warnings: {primary['warnings'] if primary else 'file not readable'}",
        })

    cross_checks = []
    for title, upload in [(check1_title, check1_pdf), (check2_title, check2_pdf)]:
        parsed = save_and_parse(upload)
        if parsed and parsed["records"]:
            cross_checks.append((title or "Untitled source", parsed["records"]))

    results = compare_verses(primary["records"], cross_checks)

    global _last_comparison
    _last_comparison = {
        "scripture_name": scripture_name,
        "primary_title": primary_title,
        "cross_check_titles": [t for t, _ in cross_checks],
        "results": results,
    }

    counts = {"matched": 0, "mismatch": 0, "not_checked": 0}
    for r in results:
        counts[r["cross_check_status"]] += 1

    return templates.TemplateResponse(request, "results.html", {
        "total": len(results),
        "counts": counts,
        "results": results,
        "warnings": primary["warnings"],
    })


@app.post("/load-to-database", response_class=HTMLResponse)
def load_to_database(request: Request):
    if not _last_comparison:
        return HTMLResponse("No comparison run yet.", status_code=400)

    primary_meta = {
        "title": _last_comparison["primary_title"], "author": None, "editor": None,
        "year": None, "institution": None, "url": None, "license": None,
        "commercial_use_allowed": None, "role": "primary", "notes": None,
    }
    cross_check_metas = {
        title: {"title": title, "author": None, "editor": None, "year": None,
                "institution": None, "url": None, "license": None,
                "commercial_use_allowed": None, "role": "cross_check", "notes": None}
        for title in _last_comparison["cross_check_titles"]
    }

    outcome = write_comparison_results(
        _last_comparison["scripture_name"], primary_meta, cross_check_metas, _last_comparison["results"]
    )
    return HTMLResponse(
        f"<p>Loaded {outcome['written']} verses. "
        f"Skipped {outcome['skipped_approved_or_rejected']} already scholar-approved/rejected verses.</p>"
        f"<p><a href='/review'>Go to scholar review</a></p>"
    )


@app.get("/review", response_class=HTMLResponse)
def review(request: Request, scripture: str = None, chapter: str = None, status: str = "pending"):
    """Shows every verse, in chapter/verse order, not just the flagged ones,
    per the scholar's request: review flows 1.1, 1.2, 1.3... straight
    through, with each verse's cross-check readings visible whether or not
    it's flagged, so a clean verse is still confirmable, not just skipped.

    Filters by scripture AND chapter (not chapter alone): with more than
    one scripture in the database, "chapter 1" is ambiguous on its own
    (e.g. Bhagavad Gita chapter 1 vs. Isha Upanishad's single chapter,
    both stored as chapter=1), so the chapter dropdown is scoped to
    whichever scripture is selected.

    status defaults to "pending" (the day-to-day review queue) but can be
    set to "approved", "needs_review", or "all", so a scholar can look back
    at verses already decided on and, if something looks wrong on a second
    look, correct it via the same /decide endpoint rather than it being a
    one-way, no-going-back action.
    """
    chapter_int = int(chapter) if chapter else None

    conn = psycopg.connect(DSN)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT scripture FROM verses ORDER BY scripture")
    scriptures = [r[0] for r in cur.fetchall()]
    if scripture is None and scriptures:
        scripture = scriptures[0]

    cur.execute(
        """
        SELECT v.id, v.scripture, v.chapter, v.verse_number, v.sanskrit_text,
               v.cross_check_status, v.scholar_status,
               array_agg(s.title) FILTER (WHERE r.verse_id IS NOT NULL) AS cc_titles,
               array_agg(r.raw_text) FILTER (WHERE r.verse_id IS NOT NULL) AS cc_texts
        FROM verses v
        LEFT JOIN verse_source_readings r ON r.verse_id = v.id
        LEFT JOIN sources s ON s.id = r.source_id
        WHERE (%(status)s::text = 'all' OR v.scholar_status = %(status)s::text)
          AND (%(scripture)s::text IS NULL OR v.scripture = %(scripture)s::text)
          AND (%(chapter)s::int IS NULL OR v.chapter = %(chapter)s::int)
        GROUP BY v.id, v.scripture, v.chapter, v.verse_number, v.sanskrit_text, v.cross_check_status, v.scholar_status
        ORDER BY v.chapter, v.verse_number
        """,
        {"scripture": scripture, "chapter": chapter_int, "status": status},
    )
    verses = [
        (id_, scripture_, ch, verse, text, cc_status, s_status, list(zip(cc_titles or [], cc_texts or [])))
        for (id_, scripture_, ch, verse, text, cc_status, s_status, cc_titles, cc_texts) in cur.fetchall()
    ]

    cur.execute("SELECT DISTINCT chapter FROM verses WHERE scripture = %s ORDER BY chapter", (scripture,))
    chapters = [r[0] for r in cur.fetchall()]

    cur.close()
    conn.close()
    return templates.TemplateResponse(request, "review.html", {
        "verses": verses,
        "scriptures": scriptures,
        "selected_scripture": scripture,
        "chapters": chapters,
        "selected_chapter": chapter_int,
        "selected_status": status,
    })


@app.post("/review/{verse_id}/decide")
def decide(verse_id: int, decision: str = Form(...), corrected_text: str = Form("")):
    """decision is one of:
      "approve_ours"           - our stored text is correct, approve as-is.
      "approve_other:<index>"  - the cross-check source at that index (0-based,
                                  same order as displayed) is correct; our
                                  stored text is REPLACED with it (logged in
                                  content_audit_log), then approved.
      "approve_corrected"      - neither source is right; corrected_text
                                  (typed by the scholar) replaces our stored
                                  text (logged), then approved.
      "needs_review"           - no change, just flags it for later attention.
    Nothing is silently overwritten: any text change is recorded as an
    old-value/new-value pair in content_audit_log before the verse row itself
    changes, per rules.md Section 5 (every correction needs an audit trail).
    """
    conn = psycopg.connect(DSN)
    cur = conn.cursor()

    cur.execute("SELECT sanskrit_text, verse_number FROM verses WHERE id = %s", (verse_id,))
    row = cur.fetchone()
    if row is None:
        cur.close()
        conn.close()
        return HTMLResponse(f"<p>Verse {verse_id} not found.</p>", status_code=404)
    old_text, verse_number = row

    new_text = None
    if decision.startswith("approve_other:"):
        source_index = int(decision.split(":", 1)[1])
        cur.execute(
            """
            SELECT r.raw_text FROM verse_source_readings r
            WHERE r.verse_id = %s ORDER BY r.source_id LIMIT 1 OFFSET %s
            """,
            (verse_id, source_index),
        )
        source_row = cur.fetchone()
        if source_row is None or not source_row[0]:
            cur.close()
            conn.close()
            return HTMLResponse("<p>Could not find that cross-check source's text.</p>", status_code=400)
        new_text = clean_for_storage(source_row[0], verse_number)
        decision = "approve_other"  # normalize for the audit log's "reason" field
    elif decision == "approve_corrected":
        if not corrected_text.strip():
            cur.close()
            conn.close()
            return HTMLResponse("<p>No corrected text was provided.</p>", status_code=400)
        new_text = corrected_text.strip()

    status = "needs_review" if decision == "needs_review" else "approved"

    if new_text is not None and new_text != old_text:
        cur.execute(
            """
            INSERT INTO content_audit_log (table_name, record_id, changed_by, old_values, new_values, reason)
            VALUES ('verses', %s, %s, %s, %s, %s)
            """,
            (verse_id, "scholar_review_ui", psycopg.types.json.Json({"sanskrit_text": old_text}),
             psycopg.types.json.Json({"sanskrit_text": new_text}), decision),
        )
        cur.execute(
            "UPDATE verses SET sanskrit_text = %s, scholar_status = %s, updated_at = now() WHERE id = %s",
            (new_text, status, verse_id),
        )
    else:
        cur.execute(
            "UPDATE verses SET scholar_status = %s, updated_at = now() WHERE id = %s",
            (status, verse_id),
        )

    conn.commit()
    cur.execute("SELECT sanskrit_text FROM verses WHERE id = %s", (verse_id,))
    current_text = cur.fetchone()[0]
    cur.close()
    conn.close()
    return JSONResponse({"verse_id": verse_id, "scholar_status": status, "sanskrit_text": current_text})
