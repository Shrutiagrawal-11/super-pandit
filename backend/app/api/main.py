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

app = FastAPI(title="AI Pandit API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str


class ContextVerse(BaseModel):
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
