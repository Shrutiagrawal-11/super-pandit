"""Writes compared verse records to Postgres. Never sets scholar_status to
anything but 'pending' on insert, and never overwrites a verse a scholar has
already approved or rejected. See rules.md: scholar approval is the only
thing that can move a verse to 'approved'.
"""
import json

import psycopg

DSN = "postgresql://pandit:pandit_dev_local@localhost:5432/ai_pandit"


def upsert_source(cur, meta):
    cur.execute(
        """
        INSERT INTO sources (title, author, editor, year, institution, url, license, commercial_use_allowed, role, notes)
        VALUES (%(title)s, %(author)s, %(editor)s, %(year)s, %(institution)s, %(url)s, %(license)s, %(commercial_use_allowed)s, %(role)s, %(notes)s)
        RETURNING id
        """,
        meta,
    )
    return cur.fetchone()[0]


def write_comparison_results(scripture_name, primary_source_meta, cross_check_source_metas, comparison_results, dsn=DSN):
    """cross_check_source_metas: dict of source_name -> metadata dict (same
    shape as primary_source_meta), keyed to match the 'source' field used in
    comparison_results' readings.
    """
    conn = psycopg.connect(dsn)
    cur = conn.cursor()

    primary_source_id = upsert_source(cur, primary_source_meta)
    cross_check_ids = {name: upsert_source(cur, meta) for name, meta in cross_check_source_metas.items()}

    skipped = 0
    for r in comparison_results:
        cur.execute(
            """
            INSERT INTO verses (scripture, chapter, verse_number, sanskrit_text, raw_sanskrit_text, source_citation, cross_check_status, primary_source_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (scripture, chapter, verse_number) DO UPDATE SET
                sanskrit_text = EXCLUDED.sanskrit_text,
                raw_sanskrit_text = EXCLUDED.raw_sanskrit_text,
                source_citation = EXCLUDED.source_citation,
                cross_check_status = EXCLUDED.cross_check_status,
                primary_source_id = EXCLUDED.primary_source_id,
                updated_at = now()
            WHERE verses.scholar_status NOT IN ('approved', 'rejected')
            RETURNING id
            """,
            (
                scripture_name,
                r["chapter"],
                r["verse"],
                r["primary_text"],
                r["primary_text"],
                primary_source_meta["title"],
                r["cross_check_status"],
                primary_source_id,
            ),
        )
        row = cur.fetchone()
        if row is None:
            skipped += 1
            continue
        verse_id = row[0]

        for reading in r["readings"]:
            if reading["text"] is None:
                continue
            source_id = cross_check_ids[reading["source"]]
            cur.execute(
                """
                INSERT INTO verse_source_readings (verse_id, source_id, raw_text, matches_primary)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (verse_id, source_id) DO UPDATE SET
                    raw_text = EXCLUDED.raw_text,
                    matches_primary = EXCLUDED.matches_primary
                """,
                (verse_id, source_id, reading["text"], reading["matches"]),
            )

    conn.commit()
    cur.close()
    conn.close()
    return {"written": len(comparison_results) - skipped, "skipped_approved_or_rejected": skipped}
