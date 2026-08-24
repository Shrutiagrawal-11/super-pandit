"""API server for the AI Pandit mobile app.

Run: uvicorn api.main:app --reload --port 8000  (from backend/app/)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from llm.pipeline import answer_question
from api.auth import router as auth_router
from api.library import router as library_router
from api.library_content import router as library_content_router

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


class AskRequest(BaseModel):
    question: str


class ContextVerse(BaseModel):
    verse_id: int
    scripture: str
    chapter: int
    verse_number: int
    sanskrit_text: str
    similarity: float


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
    return AskResponse(
        answer=result["answer"],
        grounded=result["grounded"],
        context_verses=result["context_verses"],
    )
