"""Extract Bhagavad Gita chapters 8-18 from GRETIL's sa_bhagavadgItA-4comm.htm
(the same primary source already used for chapters 3-7) and insert them as
pending rows, same as the existing chapters.

Structure (confirmed by direct inspection of the downloaded HTML, cross-
checked against traditional per-chapter verse counts, not guessed): each
verse (or group of verses) starts with a `<p>BhG C.V</p>` marker, or
`<p>BhG C.V-W</p>` when GRETIL groups consecutive verses under one shared
header, followed by one `<p>...</p>` block PER ACTUAL VERSE in the group,
each ending in its own `||V||`. Verse-text lines are separated by `<br />`
in most, but not all, blocks (a few verses' lines are separated by a plain
newline in the source markup instead, confirmed directly, so `<br />`
presence is NOT used as a filter here). Commentary blocks (Śrīdhara,
Madhusūdana, Viśvanātha, Baladeva) follow and are not extracted, consistent
with chapters 1-7: only the bare Sanskrit verse text is used, per the
CC BY-NC-SA licensing finding on this file's commentary (see rules.md
Section 7).

Known irregularities in this source, each individually confirmed by direct
inspection rather than caught by a general rule (an automated heuristic
attempt at this repeatedly produced false positives/negatives on real edge
cases, see PROJECT_PLAN.md Phase 0 notes):
  - BhG 8.11's own <p> tag is malformed (never closes on its own line, a
    nested <p> for the verse text sits inside it). Handled as a special case.
  - This source's chapter 13 genuinely has only 34 verses, not the 35 some
    other Gita editions use (confirmed: chapter 13's section ends with two
    closing colophons after verse 34, "trayodaśo 'dhyāyaḥ ||13||", with no
    verse 35 anywhere in the section) — this is a real edition difference,
    not a missing verse, and is left as 34 rather than fabricating a 35th.

Only the bare verse text is inserted; nothing here approves anything, all
rows land with scholar_status='pending' (the schema default), per rules.md.
"""
import re
import sys

import psycopg

DB_URL = "postgresql://pandit:pandit_dev_local@localhost:5432/ai_pandit"
GRETIL_URL = "https://gretil.sub.uni-goettingen.de/gretil/corpustei/transformations/html/sa_bhagavadgItA-4comm.htm"
CITATION = "GRETIL sa_bhagavadgItA-4comm"

MARKER_RE = re.compile(r"<p>\s*BhG\s+(\d+)\.(\d+)(?:-(\d+))?\s*</p>")
P_BLOCK_RE = re.compile(r"<p>(.*?)</p>", re.S)
VERSE_END_RE = re.compile(r"\|\|\s*(\d+)\s*\|\|\s*$")
TAG_RE = re.compile(r"<[^>]+>")

MALFORMED_MARKER_RE = re.compile(r"<p>\s*BhG\s+8\.11\s*<p>\s*(.*?)</p>\s*</p>", re.S)

# A handful of verses (confirmed: 13.34, 18.11, 18.13, 18.68) have their
# marker and verse text combined in a single <p> block ("<p>BhG C.V<br />
# line1<br />line2 ||V||</p>") instead of the usual separate marker-<p> then
# verse-<p>. This is a real, recurring structural variant in this source
# (found in more than one place, not a one-off typo like 8.11), so it's
# handled as its own general pattern rather than listing each case by hand.
COMBINED_MARKER_RE = re.compile(r"<p>\s*BhG\s+(\d+)\.(\d+)\s*<br\s*/?>\s*(.*?)</p>", re.S)

# These verses have no marker at all anywhere in the source, in either the
# standalone or combined form, confirmed by direct inspection (their text
# sits immediately after the preceding verse's commentary blocks, with no
# "<p>BhG C.V</p>" or "<p>BhG C.V<br />" of their own). Each was individually
# located by its own unambiguous "||V||" ending within its chapter's section
# and checked against the expected verse number; none were guessed.
MARKERLESS_VERSES = [
    (10, 26), (12, 6), (12, 7), (15, 6), (15, 9), (15, 13), (15, 16),
    (16, 2), (16, 3), (16, 9), (16, 13), (17, 4), (17, 14),
]


def fetch_html():
    import urllib.request
    req = urllib.request.Request(GRETIL_URL, headers={"User-Agent": "Mozilla/5.0 (AI Pandit ingestion)"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        return resp.read().decode("utf-8")


def clean_verse_text(raw_block):
    text = raw_block.replace("<br />", "\n").replace("<br/>", "\n")
    text = TAG_RE.sub("", text)
    lines = [ln.strip() for ln in text.split("\n")]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines)


def chapter_section(html, chapter):
    headers = list(re.finditer(r"<p>\s*Bhagavadgita\s+(\d+)\s*</p>", html))
    for i, m in enumerate(headers):
        if int(m.group(1)) == chapter:
            start = m.end()
            end = headers[i + 1].start() if i + 1 < len(headers) else len(html)
            return html[start:end]
    return None


def extract_markerless_verses(html, warnings):
    """Locates each verse in MARKERLESS_VERSES by its own unambiguous
    ||V||-ending <p> block within its chapter's section, since no marker
    exists to anchor it. Warns (does not fabricate) if a chapter's section
    or the expected block can't be found.
    """
    records = []
    for chapter, verse in MARKERLESS_VERSES:
        section = chapter_section(html, chapter)
        if section is None:
            warnings.append(f"BhG {chapter}.{verse} (markerless, special case): chapter {chapter}'s section not found.")
            continue
        m = re.search(rf"<p>\s*((?:(?!</p>).)*?\|\|\s*{verse}\s*\|\|)\s*</p>", section, re.S)
        if not m:
            warnings.append(f"BhG {chapter}.{verse} (markerless, special case): expected ||{verse}|| block not found.")
            continue
        records.append({"chapter": chapter, "verse": verse, "text": clean_verse_text(m.group(1))})
    return records


def extract_chapters_8_to_18(html):
    """Returns (records, warnings).

    For each marker (single or grouped, e.g. BhG C.V or BhG C.V-W), takes
    consecutive verse-shaped <p> blocks (any block whose cleaned text ends
    in ||N||) immediately following it, one per verse number in the marker's
    range, matching each block's own closing ||N|| against the expected
    verse number to confirm alignment rather than assuming a fixed count.
    """
    records = []
    warnings = []

    bad = MALFORMED_MARKER_RE.search(html)
    if bad:
        text = clean_verse_text(bad.group(1))
        if VERSE_END_RE.search(text):
            records.append({"chapter": 8, "verse": 11, "text": text})
        else:
            warnings.append(f"BhG 8.11 (malformed marker, handled as special case): verse text didn't end with ||N||: {text[:60]!r}")
        html = html[: bad.start()] + html[bad.end() :]

    combined_spans = []
    for m in COMBINED_MARKER_RE.finditer(html):
        chapter, verse = int(m.group(1)), int(m.group(2))
        if not (8 <= chapter <= 18):
            continue
        text = clean_verse_text(m.group(3))
        end_marker = VERSE_END_RE.search(text)
        if end_marker and int(end_marker.group(1)) == verse:
            records.append({"chapter": chapter, "verse": verse, "text": text})
            combined_spans.append((m.start(), m.end()))
        else:
            warnings.append(f"BhG {chapter}.{verse} (combined marker+verse block): didn't end in ||{verse}||, skipped: {text[:60]!r}")
    # Blank out matched combined blocks so the standalone-marker pass below
    # doesn't also try to parse the leftover "BhG C.V<br />" fragment as if
    # it were its own empty marker.
    for start, end in sorted(combined_spans, reverse=True):
        html = html[:start] + html[end:]

    p_positions = [(m.start(), m.group(1)) for m in P_BLOCK_RE.finditer(html)]

    for m in MARKER_RE.finditer(html):
        chapter = int(m.group(1))
        if chapter < 8 or chapter > 18:
            continue
        verse_start = int(m.group(2))
        verse_end = int(m.group(3)) if m.group(3) else verse_start

        following = [p for p in p_positions if p[0] >= m.end()]
        following.sort(key=lambda p: p[0])

        cursor = 0
        for expected_verse in range(verse_start, verse_end + 1):
            # Skip any block that isn't verse-shaped (e.g. non-<br/> commentary
            # prose that happens to sit before the real verse block; verse
            # blocks are always the first ||N||-ending block matching the
            # EXPECTED verse number, so a non-matching end marker means this
            # block belongs to something else, not that we should give up).
            found = False
            while cursor < len(following):
                text = clean_verse_text(following[cursor][1])
                end_marker = VERSE_END_RE.search(text)
                cursor += 1
                if end_marker and int(end_marker.group(1)) == expected_verse:
                    records.append({"chapter": chapter, "verse": expected_verse, "text": text})
                    found = True
                    break
                if end_marker and int(end_marker.group(1)) > expected_verse + verse_end:
                    break  # gone too far past this marker's range, stop scanning
            if not found:
                warnings.append(f"BhG {chapter}.{expected_verse}: no matching ||{expected_verse}|| block found following its marker.")
                break

    records.extend(extract_markerless_verses(html, warnings))

    return records, warnings


def cross_check_against_markers(html, records, warnings):
    """Every explicit marker's verse range should have produced a record.
    Reports any that didn't, so a gap is never silently accepted."""
    have = {(r["chapter"], r["verse"]) for r in records}
    for m in MARKER_RE.finditer(html):
        chapter = int(m.group(1))
        if chapter < 8 or chapter > 18:
            continue
        v_start = int(m.group(2))
        v_end = int(m.group(3)) if m.group(3) else v_start
        for v in range(v_start, v_end + 1):
            if (chapter, v) not in have:
                warnings.append(f"BhG {chapter}.{v}: an explicit marker exists for this verse, but no verse text block was extracted for it.")


def main():
    print("Fetching GRETIL page...")
    html = fetch_html()
    records, warnings = extract_chapters_8_to_18(html)
    cross_check_against_markers(html, records, warnings)

    for w in warnings:
        print(f"WARNING: {w}", file=sys.stderr)

    print(f"Extracted {len(records)} verse records for chapters 8-18.")
    by_chapter = {}
    for r in records:
        by_chapter.setdefault(r["chapter"], 0)
        by_chapter[r["chapter"]] += 1
    print("Per-chapter counts:", dict(sorted(by_chapter.items())))

    if not records:
        print("Nothing to insert.", file=sys.stderr)
        sys.exit(1)

    inserted = skipped = 0
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            for r in records:
                cur.execute(
                    """
                    INSERT INTO verses (scripture, chapter, verse_number, sanskrit_text, source_citation)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (scripture, chapter, verse_number) DO NOTHING
                    RETURNING id
                    """,
                    ("Bhagavad Gita", r["chapter"], r["verse"], r["text"], CITATION),
                )
                if cur.fetchone():
                    inserted += 1
                else:
                    skipped += 1
        conn.commit()

    print(f"Inserted {inserted}, skipped {skipped} (already present).")
    print("All inserted rows have scholar_status='pending'.")


if __name__ == "__main__":
    main()
