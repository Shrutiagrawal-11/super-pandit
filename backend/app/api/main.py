"""API server for the AI Pandit mobile app.

Run: uvicorn api.main:app --reload --port 8000  (from backend/app/)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from llm.pipeline import answer_question
from api.auth import router as auth_router
from api.library import router as library_router
from api.library_content import router as library_content_router
from api.pronunciation import router as pronunciation_router
from api.practice import router as practice_router

VERSE_AUDIO_DIR = Path(__file__).parent.parent / "static" / "verse_audio"
VERSE_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="AI Pandit API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(library_router)
app.include_router(library_content_router)
app.include_router(pronunciation_router)
app.include_router(practice_router)
app.mount("/verse_audio", StaticFiles(directory=VERSE_AUDIO_DIR), name="verse_audio")


def verse_audio_path(scripture, chapter, verse_number):
    """Filename convention Vagdhenu output must be dropped into, per
    OPERATIONS.md Section 8. No DB column for this: presence on disk is
    the source of truth, since rendering happens on a separate GPU machine
    and this only needs to answer "does verified audio exist right now".
    """
    slug = f"{scripture.lower().replace(' ', '_')}_{chapter}_{verse_number}.wav"
    return VERSE_AUDIO_DIR / slug, slug


class AskRequest(BaseModel):
    question: str


class ContextVerse(BaseModel):
    verse_id: int
    scripture: str
    chapter: int
    verse_number: int
    sanskrit_text: str
    similarity: float
    audio_url: str | None = None


class AskResponse(BaseModel):
    answer: str
    grounded: bool
    context_verses: list[ContextVerse]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    result = answer_question(req.question)
    verses = []
    for v in result["context_verses"]:
        path, slug = verse_audio_path(v["scripture"], v["chapter"], v["verse_number"])
        verses.append({**v, "audio_url": f"/verse_audio/{slug}" if path.exists() else None})
    return AskResponse(
        answer=result["answer"],
        grounded=result["grounded"],
        context_verses=verses,
    )
