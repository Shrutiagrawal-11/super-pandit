"""Real chapter listing, built from whatever's actually approved right now.
No guest gate here, unlike saved_items/reading_progress, browsing what
scripture exists isn't a personal-data feature.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg
from fastapi import APIRouter

from core.config import DATABASE_URL

router = APIRouter()


@router.get("/library/chapters")
def list_chapters():
    conn = psycopg.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT scripture, chapter, count(*) AS verse_count
        FROM verses
        WHERE scholar_status = 'approved'
        GROUP BY scripture, chapter
        ORDER BY scripture, chapter
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{"scripture": r[0], "chapter": r[1], "verse_count": r[2]} for r in rows]
