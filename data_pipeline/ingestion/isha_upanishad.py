"""Extract the Isha Upanishad from GRETIL's transformation of
sa_IzopaniSad-or-IzAvAsyopaniSadkANva-recension-comm.htm and insert as
pending rows, same trust process already used for the Gita: bare verse
text only, nothing pre-approved.

Structure (confirmed by direct inspection of the downloaded HTML, not
guessed): every verse is a single self-contained block,
`<p><span class="bold">...verse text (possibly multi-line)... || IsUp_N ||
</span></p>`, with no separate marker paragraph and no markerless verses,
unlike the Gita source. All 18 verses use this exact pattern; confirmed
by grepping every "IsUp_N" marker in the file and finding N = 1..18 with
none missing or duplicated, matching the traditional count for this
Upanishad exactly.

This file's commentary (attributed to Śaṃkara) is licensed CC BY-NC-SA
4.0 (confirmed in the file's own header) — same situation as the Gita's
4-commentary source, so, consistent with rules.md Section 7, only the
bare Sanskrit verse text is extracted here, never the commentary.
"""
import re

import psycopg

from write_db import DSN, upsert_source

GRETIL_URL = (
    "https://gretil.sub.uni-goettingen.de/gretil/corpustei/transformations/html/"
    "sa_IzopaniSad-or-IzAvAsyopaniSadkANva-recension-comm.htm"
)
CITATION = "GRETIL sa_IzopaniSad-or-IzAvAsyopaniSadkANva-recension-comm"
SCRIPTURE = "Isha Upanishad"

# Anchored to NOT cross a "</p>" or another "<p>" boundary inside the
# captured group, otherwise a non-greedy match can stretch across several
# earlier <p><span class="bold">...</span></p> blocks (e.g. the standalone
# "oṃ" invocation lines before verse 1) to reach the first "IsUp_N" marker,
# silently swallowing unrelated preceding text into the verse (confirmed by
# a first attempt that produced this exact bug on verse 1).
VERSE_BLOCK_RE = re.compile(
    r'<p><span class="bold">((?:(?!</?p\b).)*?)\|\|\s*IsUp_(\d+)\s*\|\|</span></p>', re.S
)
TAG_RE = re.compile(r"<[^>]+>")


def fetch_html():
    import urllib.request

    req = urllib.request.Request(GRETIL_URL, headers={"User-Agent": "Mozilla/5.0 (AI Pandit ingestion)"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        return resp.read().decode("utf-8")


def clean_verse_text(raw_block):
    text = TAG_RE.sub("", raw_block)
    lines = [ln.strip() for ln in text.split("\n")]
    lines = [ln for ln in lines if ln]
    return " ".join(lines).strip()


def extract_verses(html):
    records = []
    for match in VERSE_BLOCK_RE.finditer(html):
        raw_text, verse_number = match.group(1), int(match.group(2))
        text = clean_verse_text(raw_text)
        records.append({"verse_number": verse_number, "sanskrit_text": text})
    records.sort(key=lambda r: r["verse_number"])
    return records


def cross_check_against_markers(html, records):
    found_numbers = {r["verse_number"] for r in records}
    all_markers = {int(n) for n in re.findall(r"IsUp_(\d+)\s*\|\|", html)}
    missing = all_markers - found_numbers
    if missing:
        raise ValueError(f"Markers found in source but not extracted: {sorted(missing)}")
    expected = set(range(1, 19))
    if found_numbers != expected:
        raise ValueError(f"Expected verses 1-18, got {sorted(found_numbers)}")


SOURCE_META = {
    "title": CITATION,
    "author": None,
    "editor": None,
    "year": None,
    "institution": "GRETIL",
    "url": GRETIL_URL,
    "license": None,
    "commercial_use_allowed": None,
    "role": "primary",
    "notes": "Bare verse text only; commentary excluded (CC BY-NC-SA 4.0, not used per rules.md Section 7).",
}


def write_to_db(records):
    conn = psycopg.connect(DSN)
    cur = conn.cursor()

    source_id = upsert_source(cur, SOURCE_META)

    written = 0
    skipped = 0
    for r in records:
        cur.execute(
            """
            INSERT INTO verses (scripture, chapter, verse_number, sanskrit_text, raw_sanskrit_text, source_citation, primary_source_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (scripture, chapter, verse_number) DO UPDATE SET
                sanskrit_text = EXCLUDED.sanskrit_text,
                raw_sanskrit_text = EXCLUDED.raw_sanskrit_text,
                source_citation = EXCLUDED.source_citation,
                primary_source_id = EXCLUDED.primary_source_id,
                updated_at = now()
            WHERE verses.scholar_status NOT IN ('approved', 'rejected')
            RETURNING id
            """,
            (SCRIPTURE, 1, r["verse_number"], r["sanskrit_text"], r["sanskrit_text"], CITATION, source_id),
        )
        row = cur.fetchone()
        if row is None:
            skipped += 1
        else:
            written += 1

    conn.commit()
    cur.close()
    conn.close()
    return written, skipped


if __name__ == "__main__":
    html = fetch_html()
    records = extract_verses(html)
    cross_check_against_markers(html, records)
    print(f"Extracted {len(records)} verses.")
    for r in records:
        print(f"  IsUp {r['verse_number']}: {r['sanskrit_text'][:60]}...")

    written, skipped = write_to_db(records)
    print(f"Wrote {written} verse(s), skipped {skipped} already scholar-approved/rejected.")
