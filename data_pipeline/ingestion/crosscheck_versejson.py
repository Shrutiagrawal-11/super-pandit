"""Register verse.json (github.com/praneshp1org/Bhagavad-Gita-JSON-data,
sourced from vedicscriptures.github.io) as a cross_check source, and compare
it against every verse already in `verses`, using compare.py's Devanagari-
based comparison (see compare.py's module docstring for why: verse.json's
transliteration field is not strict IAST and can't be safely converted).

Only the bare Sanskrit is used, per the licensing discussion: the ancient
verse text is public domain regardless of the repo's missing LICENSE file,
but the word_meanings field (likely drawn from a named modern commentator)
is not touched here or anywhere in this pipeline. The full verse.json file
itself is kept as-is and not modified; this script only reads it.
"""
import json

import psycopg

from compare import compare_verses

DB_URL = "postgresql://pandit:pandit_dev_local@localhost:5432/ai_pandit"
VERSE_JSON_PATH = "/Users/shruti/Desktop/yantras/verse.json"

SOURCE_META = {
    "title": "Bhagavad-Gita-JSON-data (verse.json)",
    "author": None,
    "editor": None,
    "year": None,
    "institution": "vedicscriptures.github.io (via praneshp1org/Bhagavad-Gita-JSON-data)",
    "url": "https://github.com/praneshp1org/Bhagavad-Gita-JSON-data/blob/main/verse.json",
    "license": "unlicensed repo; Sanskrit verse text itself is public domain, so used for that field only",
    "commercial_use_allowed": True,
    "role": "cross_check",
    "notes": "Only the 'text' (Devanagari) field is used, not 'transliteration' (informal romanization, unsafe to auto-convert) or 'word_meanings' (not used anywhere in this pipeline).",
}


def main():
    with open(VERSE_JSON_PATH, encoding="utf-8") as f:
        entries = json.load(f)
    cross_check_records = [{"chapter": e["chapter_number"], "verse": e["verse_number"], "text": e["text"]} for e in entries]

    conn = psycopg.connect(DB_URL)
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO sources (title, author, editor, year, institution, url, license, commercial_use_allowed, role, notes)
        VALUES (%(title)s, %(author)s, %(editor)s, %(year)s, %(institution)s, %(url)s, %(license)s, %(commercial_use_allowed)s, %(role)s, %(notes)s)
        RETURNING id
        """,
        SOURCE_META,
    )
    source_id = cur.fetchone()[0]

    cur.execute("SELECT id, chapter, verse_number, sanskrit_text, cross_check_status FROM verses")
    db_rows = cur.fetchall()
    primary_records = [{"chapter": r[1], "verse": r[2], "text": r[3]} for r in db_rows]
    status_by_key = {(r[1], r[2]): r[4] for r in db_rows}
    id_by_key = {(r[1], r[2]): r[0] for r in db_rows}

    results = compare_verses(primary_records, [("verse.json", cross_check_records)])

    matched = mismatch = unconverted = not_found = soft_matched = 0
    mismatches, soft_matches, unconvertible = [], [], []
    for r in results:
        verse_id = id_by_key[(r["chapter"], r["verse"])]
        reading = r["readings"][0]

        cur.execute(
            """
            INSERT INTO verse_source_readings (verse_id, source_id, raw_text, matches_primary)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (verse_id, source_id) DO UPDATE SET
                raw_text = EXCLUDED.raw_text, matches_primary = EXCLUDED.matches_primary
            """,
            (verse_id, source_id, reading["text"] or "", reading["matches"]),
        )

        if reading["unconverted"]:
            unconverted += 1
            unconvertible.append((r["chapter"], r["verse"]))
        elif reading["matches"] is None:
            not_found += 1
        elif reading["matches"] and reading["diff_reason"]:
            soft_matched += 1
            soft_matches.append((r["chapter"], r["verse"], reading["diff_reason"]))
            if status_by_key[(r["chapter"], r["verse"])] == "not_checked":
                cur.execute("UPDATE verses SET cross_check_status = 'matched' WHERE id = %s", (verse_id,))
        elif reading["matches"]:
            matched += 1
            if status_by_key[(r["chapter"], r["verse"])] == "not_checked":
                cur.execute("UPDATE verses SET cross_check_status = 'matched' WHERE id = %s", (verse_id,))
        else:
            mismatch += 1
            mismatches.append((r["chapter"], r["verse"], r["primary_text"], reading["text"]))
            cur.execute("UPDATE verses SET cross_check_status = 'mismatch' WHERE id = %s", (verse_id,))

    conn.commit()
    cur.close()
    conn.close()

    print(f"Registered source id={source_id}.")
    print(
        f"Compared {len(results)} DB verses against verse.json: "
        f"{matched} matched, {soft_matched} soft-matched (disclosed minor diff), "
        f"{mismatch} mismatch, {unconverted} unconvertible script, {not_found} not found."
    )
    if soft_matches:
        print("\nSoft matches (agree in content, differ in a known, disclosed way):")
        for ch, vn, reason in soft_matches:
            print(f"  BhG {ch}.{vn} - {reason}")
    if unconvertible:
        print(f"\nUnconvertible (script/convention unclear, needs human alignment): {unconvertible}")
    if mismatches:
        print("\nReal mismatches (flagged for scholar review, not auto-resolved):")
        for ch, vn, ours, theirs in mismatches:
            print(f"  BhG {ch}.{vn}")
            print(f"    ours (DB) : {ours}")
            print(f"    verse.json: {theirs}")


if __name__ == "__main__":
    main()
