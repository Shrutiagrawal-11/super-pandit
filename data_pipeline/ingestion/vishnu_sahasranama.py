"""Extract the Vishnu Sahasranama from GRETIL's electronic text of the
Mahabharata Book 13 (Anusasanaparvan), chapter 135 (Bombay/critical-edition
numbering used by this e-text; this is where the thousand-names hymn
actually sits, not the traditional Southern-recension "13.149-150").

There is no standalone GRETIL file for the Sahasranama, it's this one
chapter inside the full book-13 text (prepared by Muneo Tokunaga, revised
by John Smith). Per the user's explicit choice, the entire chapter 135 is
extracted verse-by-verse: frame narrative, dhyana verses, the ~108
name-verses, phalashruti, and the appended closing hymns, exactly as
GRETIL's own verse numbering (13,135.NNN) has it, nothing trimmed at that
level.

What IS excluded (confirmed by direct inspection, not guessed): every
apparatus/interpolation line marked with a GRETIL "*NNNN_NN" (manuscript
variant reading) or "@NNN_NNNN" (larger interpolated passage found only in
some manuscripts) suffix. The largest of these, attached to verse 26, is a
177-line interpolation containing an entirely different hymn (on the
Savitri/Gayatri mantra and the sun-gods) that isn't part of the
Sahasranama itself, confirmed by reading it directly; per the user's
decision, all such apparatus text is excluded throughout the chapter, not
just this one instance, keeping each verse's stored text to the base
critical-edition reading only.

Only bare Sanskrit verse text is inserted; nothing here approves anything,
all rows land with scholar_status='pending' (the schema default).
"""
import re

import psycopg

from write_db import DSN, upsert_source

GRETIL_URL = "https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/2_epic/mbh/mbh_13_u.htm"
CITATION = "GRETIL Mahabharata Book 13 (Anusasanaparvan), ch. 135 (ed. Tokunaga/Smith)"
SCRIPTURE = "Vishnu Sahasranama"
CHAPTER = 135

# Matches only base-text lines for chapter 135: "13,135.NNN" optionally
# followed by a single lowercase pada letter (a/b/c/d/e/f...), with NO
# "*" (variant reading) or "@" (interpolation block) suffix. Lines with
# those suffixes are apparatus/interpolated text, deliberately excluded.
LINE_RE = re.compile(
    r'^13,135\.(\d+)([a-z]?)\t(.*?)<BR>\s*$', re.MULTILINE
)


def fetch_html():
    import urllib.request

    req = urllib.request.Request(GRETIL_URL, headers={"User-Agent": "Mozilla/5.0 (AI Pandit ingestion)"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        return resp.read().decode("utf-8")


def extract_verses(html):
    """Groups consecutive base-text lines by their verse number (the part
    before the pada letter), in file order, concatenating pada lines (and
    any bare speaker-attribution line, which has no pada letter at all)
    into one verse record.
    """
    by_verse = {}
    order = []
    for match in LINE_RE.finditer(html):
        verse_number, pada, text = int(match.group(1)), match.group(2), match.group(3).strip()
        if not text:
            continue
        if verse_number not in by_verse:
            by_verse[verse_number] = []
            order.append(verse_number)
        by_verse[verse_number].append(text)

    records = []
    for vn in order:
        combined = " ".join(by_verse[vn])
        records.append({"verse_number": vn, "sanskrit_text": combined})
    return records


def cross_check_against_source(html, records):
    all_verse_numbers = {int(m) for m in re.findall(r"^13,135\.(\d+)", html, re.MULTILINE)}
    extracted_numbers = {r["verse_number"] for r in records}
    missing = all_verse_numbers - extracted_numbers
    if missing:
        raise ValueError(f"Verse numbers present in source but not extracted: {sorted(missing)}")
    if sorted(extracted_numbers) != list(range(1, max(extracted_numbers) + 1)):
        gaps = sorted(set(range(1, max(extracted_numbers) + 1)) - extracted_numbers)
        raise ValueError(f"Gaps in verse numbering: {gaps}")


SOURCE_META = {
    "title": CITATION,
    "author": None,
    "editor": "Muneo Tokunaga (rev. John Smith)",
    "year": None,
    "institution": "GRETIL",
    "url": GRETIL_URL,
    "license": None,
    "commercial_use_allowed": None,
    "role": "primary",
    "notes": (
        "Extracted from the full Mahabharata Book 13 e-text, chapter 135 only. "
        "All '*NNNN_NN' and '@NNN_NNNN' apparatus/interpolation lines excluded "
        "(base critical-edition text only); largest exclusion is a 177-line "
        "interpolated Savitri/Gayatri hymn attached to verse 26, unrelated to "
        "the Sahasranama itself, confirmed by direct inspection."
    ),
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
            (SCRIPTURE, CHAPTER, r["verse_number"], r["sanskrit_text"], r["sanskrit_text"], CITATION, source_id),
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
    cross_check_against_source(html, records)
    print(f"Extracted {len(records)} verses.")
    for r in records[:5]:
        print(f"  {r['verse_number']}: {r['sanskrit_text'][:70]}...")
    print("  ...")
    for r in records[-3:]:
        print(f"  {r['verse_number']}: {r['sanskrit_text'][:70]}...")

    written, skipped = write_to_db(records)
    print(f"Wrote {written} verse(s), skipped {skipped} already scholar-approved/rejected.")
