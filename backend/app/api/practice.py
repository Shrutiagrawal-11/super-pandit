"""Phase 5: daily practice tracking. Reuses `practice_sessions`
(001_init_schema.sql), unused until now — one row per completed activity,
append-only like pronunciation_attempts. Streak is computed on read from
distinct activity_date, not stored, so it can never drift from the raw log.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from core.config import DATABASE_URL
from api.auth import current_user_id

router = APIRouter()

DAILY_PROMPTS = [
    "Reflect: where in today did you act without attachment to the result?",
    "Reflect: what is one duty (dharma) you carried out today, big or small?",
    "Reflect: notice one moment today you reacted from fear instead of clarity.",
]


class LogRequest(BaseModel):
    activity_type: str
    score: float | None = None


@router.get("/practice/today")
def today_prompt():
    day_index = date.today().toordinal() % len(DAILY_PROMPTS)
    return {"date": date.today().isoformat(), "prompt": DAILY_PROMPTS[day_index]}


@router.post("/practice/log")
def log_activity(req: LogRequest, user_id: int = Depends(current_user_id)):
    conn = psycopg.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO practice_sessions (user_id, activity_date, activity_type, score) VALUES (%s, %s, %s, %s)",
        (user_id, date.today(), req.activity_type, req.score),
    )
    conn.commit()
    cur.close()
    conn.close()
    return {"status": "logged"}


@router.get("/practice/streak")
def get_streak(user_id: int = Depends(current_user_id)):
    conn = psycopg.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute(
        "SELECT DISTINCT activity_date FROM practice_sessions WHERE user_id = %s ORDER BY activity_date DESC",
        (user_id,),
    )
    days = {r[0] for r in cur.fetchall()}
    cur.close()
    conn.close()

    streak = 0
    cursor_day = date.today()
    if cursor_day not in days:
        cursor_day -= timedelta(days=1)  # today not yet logged shouldn't zero out yesterday's streak
    while cursor_day in days:
        streak += 1
        cursor_day -= timedelta(days=1)

    return {"current_streak": streak, "active_today": date.today() in days}


@router.get("/practice/history")
def practice_history(user_id: int = Depends(current_user_id)):
    conn = psycopg.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT activity_date, activity_type, score FROM practice_sessions
        WHERE user_id = %s ORDER BY activity_date DESC LIMIT 90
        """,
        (user_id,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        {"date": r[0].isoformat(), "activity_type": r[1], "score": float(r[2]) if r[2] is not None else None}
        for r in rows
    ]
