"""Saved verses and reading progress, both require a signed-in user.
Guests can use /ask freely, but nothing in this file, so there's nowhere
per-guest state could accidentally get attributed to the wrong person.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from core.config import DATABASE_URL
from api.auth import current_user_id

router = APIRouter()


class SaveRequest(BaseModel):
    verse_id: int
    note: str | None = None


class SavedItem(BaseModel):
    verse_id: int
    scripture: str
    chapter: int
    verse_number: int
    sanskrit_text: str
    note: str | None


class ProgressRequest(BaseModel):
    scripture: str
    chapter: int
    verse_number: int


@router.get("/library/saved", response_model=list[SavedItem])
def list_saved(user_id: int = Depends(current_user_id)):
    conn = psycopg.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT v.id, v.scripture, v.chapter, v.verse_number, v.sanskrit_text, s.note
        FROM saved_items s JOIN verses v ON v.id = s.verse_id
        WHERE s.user_id = %s ORDER BY s.created_at DESC
        """,
        (user_id,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        SavedItem(verse_id=r[0], scripture=r[1], chapter=r[2], verse_number=r[3], sanskrit_text=r[4], note=r[5])
        for r in rows
    ]


@router.post("/library/saved")
def save_item(req: SaveRequest, user_id: int = Depends(current_user_id)):
    conn = psycopg.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO saved_items (user_id, verse_id, note) VALUES (%s, %s, %s)
        ON CONFLICT (user_id, verse_id) DO UPDATE SET note = EXCLUDED.note
        """,
        (user_id, req.verse_id, req.note),
    )
    conn.commit()
    cur.close()
    conn.close()
    return {"status": "saved"}


@router.delete("/library/saved/{verse_id}")
def unsave_item(verse_id: int, user_id: int = Depends(current_user_id)):
    conn = psycopg.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("DELETE FROM saved_items WHERE user_id = %s AND verse_id = %s", (user_id, verse_id))
    conn.commit()
    cur.close()
    conn.close()
    return {"status": "removed"}


@router.get("/library/progress")
def get_progress(user_id: int = Depends(current_user_id)):
    conn = psycopg.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT scripture, chapter, verse_number, updated_at FROM reading_progress WHERE user_id = %s", (user_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        {"scripture": r[0], "chapter": r[1], "verse_number": r[2], "updated_at": r[3].isoformat()}
        for r in rows
    ]


@router.post("/library/progress")
def set_progress(req: ProgressRequest, user_id: int = Depends(current_user_id)):
    conn = psycopg.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO reading_progress (user_id, scripture, chapter, verse_number, updated_at)
        VALUES (%s, %s, %s, %s, now())
        ON CONFLICT (user_id, scripture) DO UPDATE
            SET chapter = EXCLUDED.chapter, verse_number = EXCLUDED.verse_number, updated_at = now()
        """,
        (user_id, req.scripture, req.chapter, req.verse_number),
    )
    conn.commit()
    cur.close()
    conn.close()
    return {"status": "updated"}
