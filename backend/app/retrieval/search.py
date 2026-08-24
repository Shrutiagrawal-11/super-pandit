"""Vector similarity search over scholar-approved verse embeddings.

Only ever searches verse_embeddings joined against approved verses, so an
unapproved verse can never surface as retrieved context (see rules.md).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer

from core.config import DATABASE_URL, EMBEDDING_MODEL_NAME, RETRIEVAL_TOP_K

_model = None


def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model


def search(question, top_k=None):
    """Returns a list of dicts: scripture, chapter, verse_number,
    sanskrit_text, similarity — ordered by similarity descending.
    """
    top_k = top_k or RETRIEVAL_TOP_K
    query_vector = _get_model().encode([question], normalize_embeddings=True)[0]

    conn = psycopg.connect(DATABASE_URL)
    register_vector(conn)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT v.scripture, v.chapter, v.verse_number, v.sanskrit_text,
               1 - (e.embedding <=> %s) AS similarity
        FROM verse_embeddings e
        JOIN verses v ON v.id = e.verse_id
        WHERE v.scholar_status = 'approved'
        ORDER BY e.embedding <=> %s
        LIMIT %s
        """,
        (query_vector, query_vector, top_k),
    )
    results = [
        {
            "scripture": scripture,
            "chapter": chapter,
            "verse_number": verse_number,
            "sanskrit_text": sanskrit_text,
            "similarity": float(similarity),
        }
        for scripture, chapter, verse_number, sanskrit_text, similarity in cur.fetchall()
    ]
    cur.close()
    conn.close()
    return results


if __name__ == "__main__":
    import sys as _sys

    q = " ".join(_sys.argv[1:]) or "What does Krishna say about duty?"
    for r in search(q):
        print(f"{r['scripture']} {r['chapter']}.{r['verse_number']} (sim={r['similarity']:.3f}): {r['sanskrit_text']}")
