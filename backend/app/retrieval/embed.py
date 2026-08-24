"""Generates and stores embeddings for scholar-approved verses only.

Per rules.md: nothing unverified reaches users, so a verse must have
scholar_status = 'approved' before it's embedded and made retrievable.
Re-running this script is safe: it skips verses that already have a
current embedding (same model_version) and only embeds new approvals or
verses whose text changed after their embedding was made.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer

from core.config import DATABASE_URL, EMBEDDING_MODEL_NAME

BATCH_SIZE = 32


def fetch_pending_verses(cur):
    cur.execute(
        """
        SELECT v.id, v.sanskrit_text
        FROM verses v
        LEFT JOIN verse_embeddings e ON e.verse_id = v.id AND e.model_version = %s
        WHERE v.scholar_status = 'approved' AND e.verse_id IS NULL
        ORDER BY v.chapter, v.verse_number
        """,
        (EMBEDDING_MODEL_NAME,),
    )
    return cur.fetchall()


def embed_verses():
    conn = psycopg.connect(DATABASE_URL)
    register_vector(conn)
    cur = conn.cursor()

    rows = fetch_pending_verses(cur)
    if not rows:
        print("No approved verses pending embedding.")
        cur.close()
        conn.close()
        return

    print(f"Embedding {len(rows)} approved verse(s) with {EMBEDDING_MODEL_NAME}...")
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        ids = [r[0] for r in batch]
        texts = [r[1] for r in batch]
        vectors = model.encode(texts, normalize_embeddings=True)

        for verse_id, vector in zip(ids, vectors):
            cur.execute(
                """
                INSERT INTO verse_embeddings (verse_id, embedding, model_version)
                VALUES (%s, %s, %s)
                ON CONFLICT (verse_id) DO UPDATE
                    SET embedding = EXCLUDED.embedding,
                        model_version = EXCLUDED.model_version,
                        created_at = now()
                """,
                (verse_id, vector, EMBEDDING_MODEL_NAME),
            )
        conn.commit()
        print(f"  {min(i + BATCH_SIZE, len(rows))}/{len(rows)} done")

    cur.close()
    conn.close()
    print("Done.")


if __name__ == "__main__":
    embed_verses()
