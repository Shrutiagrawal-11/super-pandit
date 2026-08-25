-- Phase 4: shloka pronunciation training. A lesson wraps one verse with a
-- verified reference recording (scholar/pandit-recorded, see PROJECT_PLAN.md
-- Phase 4) -- separate from the Vagdhenu-rendered audio used for plain
-- verse playback in Phase 3, since a lesson recording is specifically
-- chosen/vetted for teaching pronunciation, not just correct TTS.

CREATE TABLE pronunciation_lessons (
    id BIGSERIAL PRIMARY KEY,
    verse_id BIGINT NOT NULL REFERENCES verses(id) ON DELETE CASCADE,
    reference_audio_url TEXT,          -- filled in once a reviewed recording exists; NULL = not ready to serve
    transliteration TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    reviewed_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (verse_id)
);

-- Append-only, one row per attempt, same shape reasoning as practice_sessions.
CREATE TABLE pronunciation_attempts (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    lesson_id BIGINT NOT NULL REFERENCES pronunciation_lessons(id) ON DELETE CASCADE,
    score NUMERIC,                     -- 0-100, overall
    phoneme_feedback JSONB,            -- array of {syllable, correct} from the scoring model
    scorer_version TEXT NOT NULL,      -- which model/stub produced this score, for later re-scoring/audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX pronunciation_attempts_user_idx ON pronunciation_attempts (user_id, created_at);
