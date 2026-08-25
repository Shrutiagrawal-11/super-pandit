"""Shared verse-audio filename convention, used by both /ask (Phase 3) and
rituals.py (Phase 6 mantra recitation) -- lives outside api/main.py to avoid
those two importing each other.
"""
from pathlib import Path

VERSE_AUDIO_DIR = Path(__file__).parent.parent / "static" / "verse_audio"
VERSE_AUDIO_DIR.mkdir(parents=True, exist_ok=True)


def verse_audio_path(scripture, chapter, verse_number):
    """No DB column for this: presence on disk is the source of truth,
    since rendering happens on a separate GPU machine (OPERATIONS.md
    Section 11) and this only needs to answer "does verified audio exist
    right now".
    """
    slug = f"{scripture.lower().replace(' ', '_')}_{chapter}_{verse_number}.wav"
    return VERSE_AUDIO_DIR / slug, slug


def verse_audio_url(scripture, chapter, verse_number):
    path, slug = verse_audio_path(scripture, chapter, verse_number)
    return f"/verse_audio/{slug}" if path.exists() else None
