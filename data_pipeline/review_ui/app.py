"""Local review UI for the scripture ingestion pipeline.

Run: uvicorn app:app --reload --port 8420  (from data_pipeline/review_ui/)
Then open http://localhost:8420
"""
import sys
import tempfile
from pathlib import Path

from fastapi import FastAPI, Request, UploadFile, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

sys.path.insert(0, str(Path(__file__).parent.parent / "ingestion"))
from extract import extract_pages
from structure import parse_verses
from compare import compare_verses
from write_db import write_comparison_results

import psycopg
from write_db import DSN

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
def review(request: Request):
    conn = psycopg.connect(DSN)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, scripture, chapter, verse_number, sanskrit_text, cross_check_status, scholar_status
        FROM verses WHERE cross_check_status = 'mismatch' AND scholar_status = 'pending'
        ORDER BY chapter, verse_number
        """
    )
    mismatches = cur.fetchall()
    cur.close()
    conn.close()
    return templates.TemplateResponse(request, "review.html", {"mismatches": mismatches})


@app.post("/review/{verse_id}/decide")
def decide(verse_id: int, decision: str = Form(...)):
    status = {"approve": "approved", "reject": "rejected", "needs_review": "needs_review"}.get(decision, "needs_review")
    conn = psycopg.connect(DSN)
    cur = conn.cursor()
    cur.execute("UPDATE verses SET scholar_status = %s, updated_at = now() WHERE id = %s", (status, verse_id))
    conn.commit()
    cur.close()
    conn.close()
    return HTMLResponse(f"<p>Verse {verse_id} marked {status}. <a href='/review'>Back to review</a></p>")
