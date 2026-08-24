"""App settings, loaded from environment variables. Never hardcode secrets
here, see rules.md Section 6."""
import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://pandit:pandit_dev_local@localhost:5432/ai_pandit")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")  # the intended production LLM (GPT-5-mini), not yet wired in
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")  # temporary free-tier stand-in for local testing only
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-5-mini")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
EMBEDDING_MODEL_NAME = os.environ.get("EMBEDDING_MODEL_NAME", "BAAI/bge-m3")
RETRIEVAL_TOP_K = int(os.environ.get("RETRIEVAL_TOP_K", "5"))
