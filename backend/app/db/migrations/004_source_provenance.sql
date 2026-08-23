-- Tracks where each source document came from and its licensing status, so
-- textual correctness and legal provenance travel together (per project rule:
-- no content without a traceable, cited source, see rules.md Section 5).

CREATE TABLE sources (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT,
    editor TEXT,
    year INT,
    institution TEXT,
    url TEXT,
    license TEXT,                      -- e.g. 'CC-BY', 'CC-BY-NC-SA', 'all-rights-reserved'
    commercial_use_allowed BOOLEAN,     -- NULL = unconfirmed, do not assume true
    role TEXT NOT NULL CHECK (role IN ('primary', 'cross_check', 'reference_only')),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Links a verse's stored text to the specific source it was extracted from,
-- and records each cross-check source's reading for that verse (not just a
-- pass/fail flag), so a scholar can see the actual differing text, not just
-- that a mismatch occurred.

CREATE TABLE verse_source_readings (
    id BIGSERIAL PRIMARY KEY,
    verse_id BIGINT NOT NULL REFERENCES verses(id) ON DELETE CASCADE,
    source_id BIGINT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    raw_text TEXT NOT NULL,            -- exactly as extracted, never modified
    matches_primary BOOLEAN,           -- NULL = not found in this source for this verse
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (verse_id, source_id)
);

ALTER TABLE verses ADD COLUMN primary_source_id BIGINT REFERENCES sources(id);
