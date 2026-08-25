"""Phase 6: live-guided ritual sessions. A ritual's procedure_steps is
authored/reviewed as one complete ordered unit (architecture.md Section 5),
never assembled from fragments at answer time -- this file only ever reads
that JSONB as-is and walks it by index, it never composes a procedure.

Session state lives server-side (ritual_sessions.current_step_index) so a
dropped connection doesn't lose the user's place, per PROJECT_PLAN.md
Phase 6. Step confirmation is always explicit (POST /confirm-step) -- there
is no auto-advance path here; that is Phase 10's camera-detection scope,
deliberately not this file's job.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg
from fastapi import APIRouter, Depends, HTTPException

from core.config import DATABASE_URL
from api.auth import current_user_id
from retrieval.verse_audio import verse_audio_url as _verse_audio_url

router = APIRouter()


def _mantra_for_step(cur, step):
    verse_id = step.get("mantra_verse_id")
    if not verse_id:
        return None
    cur.execute("SELECT scripture, chapter, verse_number, sanskrit_text FROM verses WHERE id = %s", (verse_id,))
    row = cur.fetchone()
    if not row:
        return None
    scripture, chapter, verse_number, sanskrit_text = row
    return {
        "verse_id": verse_id,
        "scripture": scripture,
        "chapter": chapter,
        "verse_number": verse_number,
        "sanskrit_text": sanskrit_text,
        "citation": f"{scripture} {chapter}.{verse_number}",
        "audio_url": _verse_audio_url(scripture, chapter, verse_number),
    }


@router.get("/rituals")
def list_rituals():
    conn = psycopg.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, tradition_region FROM rituals WHERE status = 'approved' ORDER BY name"
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{"ritual_id": r[0], "name": r[1], "tradition_region": r[2]} for r in rows]


@router.get("/rituals/{ritual_id}")
def get_ritual(ritual_id: int):
    """Materials + preparation shown upfront, per architecture.md 2.3b step 3
    ('materials list shown first so the user can gather everything before
    the session proceeds') -- this is the pre-session view, not a step.
    """
    conn = psycopg.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT name, tradition_region, materials, preparation_steps, procedure_steps
        FROM rituals WHERE id = %s AND status = 'approved'
        """,
        (ritual_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        raise HTTPException(404, "Ritual not found")
    name, tradition_region, materials, preparation_steps, procedure_steps = row
    return {
        "ritual_id": ritual_id,
        "name": name,
        "tradition_region": tradition_region,
        "materials": materials,
        "preparation_steps": preparation_steps,
        "step_count": len(procedure_steps),
    }


@router.post("/rituals/{ritual_id}/sessions")
def start_session(ritual_id: int, user_id: int = Depends(current_user_id)):
    conn = psycopg.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT id FROM rituals WHERE id = %s AND status = 'approved'", (ritual_id,))
    if not cur.fetchone():
        cur.close()
        conn.close()
        raise HTTPException(404, "Ritual not found")

    cur.execute(
        "INSERT INTO ritual_sessions (user_id, ritual_id) VALUES (%s, %s) RETURNING id",
        (user_id, ritual_id),
    )
    session_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return {"session_id": session_id, "current_step_index": 0, "status": "in_progress"}


def _session_and_ritual(cur, session_id, user_id):
    cur.execute(
        """
        SELECT s.current_step_index, s.status, r.procedure_steps, r.id
        FROM ritual_sessions s JOIN rituals r ON r.id = s.ritual_id
        WHERE s.id = %s AND s.user_id = %s
        """,
        (session_id, user_id),
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Session not found")
    return row


@router.get("/rituals/sessions/{session_id}")
def get_session_step(session_id: int, user_id: int = Depends(current_user_id)):
    conn = psycopg.connect(DATABASE_URL)
    cur = conn.cursor()
    current_step_index, status, procedure_steps, ritual_id = _session_and_ritual(cur, session_id, user_id)

    if status != "in_progress" or current_step_index >= len(procedure_steps):
        cur.close()
        conn.close()
        return {"session_id": session_id, "status": status, "complete": True}

    step = procedure_steps[current_step_index]
    mantra = _mantra_for_step(cur, step)
    cur.close()
    conn.close()
    return {
        "session_id": session_id,
        "status": status,
        "complete": False,
        "current_step_index": current_step_index,
        "step_count": len(procedure_steps),
        "instruction": step["instruction"],
        "mantra": mantra,
    }


@router.post("/rituals/sessions/{session_id}/confirm-step")
def confirm_step(session_id: int, user_id: int = Depends(current_user_id)):
    """Advances exactly one step per call -- this is the only advance path
    in this phase. No confidence score, no auto-advance: manual confirmation
    is the whole point of Phase 6 versus Phase 10 (architecture.md 2.3d).
    """
    conn = psycopg.connect(DATABASE_URL)
    cur = conn.cursor()
    current_step_index, status, procedure_steps, ritual_id = _session_and_ritual(cur, session_id, user_id)

    if status != "in_progress":
        cur.close()
        conn.close()
        raise HTTPException(409, f"Session is already {status}")

    next_index = current_step_index + 1
    done = next_index >= len(procedure_steps)
    new_status = "completed" if done else "in_progress"

    cur.execute(
        "UPDATE ritual_sessions SET current_step_index = %s, status = %s, updated_at = now() WHERE id = %s",
        (next_index, new_status, session_id),
    )
    conn.commit()

    if done:
        cur.close()
        conn.close()
        return {"session_id": session_id, "status": "completed", "complete": True}

    step = procedure_steps[next_index]
    mantra = _mantra_for_step(cur, step)
    cur.close()
    conn.close()
    return {
        "session_id": session_id,
        "status": "in_progress",
        "complete": False,
        "current_step_index": next_index,
        "step_count": len(procedure_steps),
        "instruction": step["instruction"],
        "mantra": mantra,
    }


@router.post("/rituals/sessions/{session_id}/abandon")
def abandon_session(session_id: int, user_id: int = Depends(current_user_id)):
    conn = psycopg.connect(DATABASE_URL)
    cur = conn.cursor()
    _session_and_ritual(cur, session_id, user_id)
    cur.execute(
        "UPDATE ritual_sessions SET status = 'abandoned', updated_at = now() WHERE id = %s",
        (session_id,),
    )
    conn.commit()
    cur.close()
    conn.close()
    return {"session_id": session_id, "status": "abandoned"}
