"""Pronunciation scoring. Phase 4's real approach (wav2vec2 mispronunciation
detection or Montreal Forced Aligner, see architecture.md Section 4) needs a
trained model and reference-reciter audio, both GPU/data-sourcing work for
later. This stub keeps the API contract real now so the app/UI can be built
and tested end-to-end; swap score_attempt()'s body for a real model call
when it's trained, no caller changes.
"""
import random

SCORER_VERSION = "stub-v0"


def score_attempt(audio_path, transliteration):
    """Returns dict: score (0-100), phoneme_feedback (list of {syllable, correct}).

    ponytail: fake scorer, not the real acoustic model. Swap the body for a
    wav2vec2/MFA call (architecture.md Section 4) once trained; keep the
    same return shape so callers don't change.
    """
    syllables = transliteration.split()
    feedback = [{"syllable": s, "correct": random.random() > 0.2} for s in syllables]
    score = round(100 * sum(f["correct"] for f in feedback) / max(len(feedback), 1))
    return {"score": score, "phoneme_feedback": feedback}
