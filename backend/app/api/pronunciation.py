"""Phase 4: shloka pronunciation training. Lessons are curated,
scholar-approved verse+reference-audio pairs; attempts require a signed-in
user (same guest/auth split as library.py) since a streak/history is
inherently personal.
"""
import sys
import uuid
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg
from fastapi import APIRouter, Depends, HTTPException, UploadFile

from core.config import DATABASE_URL
from api.auth import current_user_id
from pronunciation.scorer import score_attempt, SCORER_VERSION

router = APIRouter()

ATTEMPTS_AUDIO_DIR = Path(__file__).parent.parent / "static" / "pronunciation_attempts"
ATTEMPTS_AUDIO_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/pronunciation/lessons")
def list_lessons():
    conn = psycopg.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT l.id, v.scripture, v.chapter, v.verse_number, v.sanskrit_text,
               l.transliteration, l.reference_audio_url
        FROM pronunciation_lessons l JOIN verses v ON v.id = l.verse_id
        WHERE l.status = 'approved'
        ORDER BY v.scripture, v.chapter, v.verse_number
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        {
            "lesson_id": r[0],
            "scripture": r[1],
            "chapter": r[2],
            "verse_number": r[3],
            "sanskrit_text": r[4],
            "transliteration": r[5],
            "reference_audio_url": r[6],
        }
        for r in rows
    ]


@router.post("/pronunciation/attempts")
async def submit_attempt(lesson_id: int, audio: UploadFile, user_id: int = Depends(current_user_id)):
    conn = psycopg.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT transliteration FROM pronunciation_lessons WHERE id = %s AND status = 'approved'", (lesson_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        raise HTTPException(404, "Lesson not found")
    transliteration = row[0]

    audio_path = ATTEMPTS_AUDIO_DIR / f"{user_id}_{lesson_id}_{uuid.uuid4().hex}.m4a"
    audio_path.write_bytes(await audio.read())

    result = score_attempt(audio_path, transliteration)

    cur.execute(
        """
        INSERT INTO pronunciation_attempts (user_id, lesson_id, score, phoneme_feedback, scorer_version)
        VALUES (%s, %s, %s, %s, %s) RETURNING id, created_at
        """,
        (user_id, lesson_id, result["score"], psycopg.types.json.Json(result["phoneme_feedback"]), SCORER_VERSION),
    )
    attempt_id, created_at = cur.fetchone()

    # Counts toward the Phase 5 daily streak automatically, no separate
    # /practice/log call needed for this activity type.
    cur.execute(
        "INSERT INTO practice_sessions (user_id, activity_date, activity_type, score) VALUES (%s, %s, 'pronunciation', %s)",
        (user_id, date.today(), result["score"]),
    )
    conn.commit()
    cur.close()
    conn.close()

    return {
        "attempt_id": attempt_id,
        "score": result["score"],
        "phoneme_feedback": result["phoneme_feedback"],
        "created_at": created_at.isoformat(),
    }


@router.get("/pronunciation/history")
def attempt_history(user_id: int = Depends(current_user_id)):
    conn = psycopg.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT a.id, a.lesson_id, a.score, a.created_at, v.scripture, v.chapter, v.verse_number
        FROM pronunciation_attempts a
        JOIN pronunciation_lessons l ON l.id = a.lesson_id
        JOIN verses v ON v.id = l.verse_id
        WHERE a.user_id = %s ORDER BY a.created_at DESC
        """,
        (user_id,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        {
            "attempt_id": r[0],
            "lesson_id": r[1],
            "score": float(r[2]) if r[2] is not None else None,
            "created_at": r[3].isoformat(),
            "scripture": r[4],
            "chapter": r[5],
            "verse_number": r[6],
        }
        for r in rows
    ]
