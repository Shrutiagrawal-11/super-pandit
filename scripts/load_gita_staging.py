"""Load staged, cross-checked Gita verses into the verses table.

Usage: python3 scripts/load_gita_staging.py data_pipeline/staging/gita_chapters_2_7.json

Inserts with scholar_status='pending' (no approval implied) and records the
cross_check_status so scholar review can be prioritized. Safe to re-run:
ON CONFLICT updates the row instead of duplicating it, EXCEPT a row a scholar
has already approved or rejected is never overwritten by a re-staged fetch,
that decision is final until a scholar changes it themselves.
"""
import json
import sys
import psycopg

DSN = "postgresql://pandit:pandit_dev_local@localhost:5432/ai_pandit"

# Staging files written before the schema rename may still use the old labels.
_STATUS_ALIASES = {"high_confidence": "matched", "unverified": "not_checked", "mismatch": "mismatch"}

def main(path):
    with open(path) as f:
        verses = json.load(f)

    conn = psycopg.connect(DSN)
    cur = conn.cursor()
    skipped = 0
    for v in verses:
        cur.execute(
            """
            INSERT INTO verses (scripture, chapter, verse_number, sanskrit_text, raw_sanskrit_text, source_citation, cross_check_status, cross_check_sources)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (scripture, chapter, verse_number) DO UPDATE SET
                sanskrit_text = EXCLUDED.sanskrit_text,
                raw_sanskrit_text = EXCLUDED.raw_sanskrit_text,
                source_citation = EXCLUDED.source_citation,
                cross_check_status = EXCLUDED.cross_check_status,
                cross_check_sources = EXCLUDED.cross_check_sources,
                updated_at = now()
            WHERE verses.scholar_status NOT IN ('approved', 'rejected')
            """,
            (
                "Bhagavad Gita",
                v["chapter"],
                v["verse_number"],
                v["sanskrit_text"],
                v["sanskrit_text"],
                v["source_citation"],
                _STATUS_ALIASES.get(v["confidence"], v["confidence"]),
                json.dumps(v["cross_check_sources"]),
            ),
        )
        if cur.rowcount == 0:
            skipped += 1
    conn.commit()
    cur.close()
    conn.close()
    print(f"Loaded {len(verses) - skipped} verses. Skipped {skipped} already scholar-approved/rejected verses (protected from overwrite).")

if __name__ == "__main__":
    main(sys.argv[1])
