CREATE EXTENSION IF NOT EXISTS vector;

-- Scripture text

CREATE TABLE verses (
    id BIGSERIAL PRIMARY KEY,
    scripture TEXT NOT NULL,           -- e.g. 'Bhagavad Gita'
    chapter INT NOT NULL,
    verse_number INT NOT NULL,
    sanskrit_text TEXT NOT NULL,       -- verbatim, sourced
    source_citation TEXT NOT NULL,     -- named source/edition this text came from
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    reviewed_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (scripture, chapter, verse_number)
);

CREATE TABLE verse_translations (
    id BIGSERIAL PRIMARY KEY,
    verse_id BIGINT NOT NULL REFERENCES verses(id) ON DELETE CASCADE,
    translator TEXT NOT NULL,
    language TEXT NOT NULL,
    text TEXT NOT NULL,
    source_citation TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    reviewed_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE commentaries (
    id BIGSERIAL PRIMARY KEY,
    verse_id BIGINT NOT NULL REFERENCES verses(id) ON DELETE CASCADE,
    commentator TEXT NOT NULL,         -- e.g. 'Adi Shankaracharya'
    language TEXT NOT NULL,
    text TEXT NOT NULL,
    source_citation TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    reviewed_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Lexicon (verified word meanings, per-verse since meaning is context-dependent)

CREATE TABLE lexicon_terms (
    id BIGSERIAL PRIMARY KEY,
    term TEXT NOT NULL,                -- Sanskrit term as it appears
    meaning TEXT NOT NULL,             -- meaning as verified for this specific usage
    source_citation TEXT NOT NULL,     -- e.g. 'Monier-Williams, CDSL v2026.1'
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    reviewed_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE term_verse_links (
    term_id BIGINT NOT NULL REFERENCES lexicon_terms(id) ON DELETE CASCADE,
    verse_id BIGINT NOT NULL REFERENCES verses(id) ON DELETE CASCADE,
    PRIMARY KEY (term_id, verse_id)
);

-- Knowledge graph (entities, names, cross-references, stories)

CREATE TABLE entities (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    entity_type TEXT NOT NULL,         -- e.g. 'deity', 'person', 'place'
    description TEXT,
    source_citation TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    reviewed_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE entity_relations (
    id BIGSERIAL PRIMARY KEY,
    subject_id BIGINT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    predicate TEXT NOT NULL,           -- e.g. 'also_known_as', 'parent_of'
    object_id BIGINT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    source_citation TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    reviewed_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE entity_verse_links (
    entity_id BIGINT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    verse_id BIGINT NOT NULL REFERENCES verses(id) ON DELETE CASCADE,
    PRIMARY KEY (entity_id, verse_id)
);

-- Retrieval

CREATE TABLE verse_embeddings (
    verse_id BIGINT PRIMARY KEY REFERENCES verses(id) ON DELETE CASCADE,
    embedding VECTOR(1024) NOT NULL,   -- dimension matches the chosen embedding model; adjust if model changes
    model_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX verse_embeddings_hnsw_idx ON verse_embeddings
    USING hnsw (embedding vector_cosine_ops);

-- Rituals (authored/reviewed as one complete ordered unit, see architecture.md Section 5)

CREATE TABLE rituals (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,                -- e.g. 'Diwali Pooja'
    tradition_region TEXT,             -- labeled variant, not silently resolved
    materials JSONB NOT NULL,          -- array of {item, quantity, note}
    preparation_steps JSONB NOT NULL,  -- ordered array of strings
    procedure_steps JSONB NOT NULL,    -- ordered array of {instruction, mantra_verse_id (nullable)}
    source_citation TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    reviewed_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE ritual_verse_links (
    ritual_id BIGINT NOT NULL REFERENCES rituals(id) ON DELETE CASCADE,
    verse_id BIGINT NOT NULL REFERENCES verses(id) ON DELETE CASCADE,
    PRIMARY KEY (ritual_id, verse_id)
);

CREATE TABLE ritual_sessions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT,                    -- FK added once users table has real auth (Phase 2)
    ritual_id BIGINT NOT NULL REFERENCES rituals(id),
    current_step_index INT NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'completed', 'abandoned')),
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Users, practice tracking, conversations (minimal shape; expands in later phases)

CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE practice_sessions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    activity_date DATE NOT NULL,
    activity_type TEXT NOT NULL,       -- e.g. 'pronunciation', 'daily_reflection'
    score NUMERIC,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX practice_sessions_user_date_idx ON practice_sessions (user_id, activity_date);

CREATE TABLE conversations (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE messages (
    id BIGSERIAL PRIMARY KEY,
    conversation_id BIGINT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    cited_verse_ids BIGINT[],          -- denormalized citation list; chat history is read far more than written
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Audit trail (append-only, see architecture.md Section 5 for why this pattern and not event sourcing / temporal tables)

CREATE TABLE content_audit_log (
    id BIGSERIAL PRIMARY KEY,
    table_name TEXT NOT NULL,
    record_id BIGINT NOT NULL,
    changed_by TEXT NOT NULL,
    old_values JSONB,
    new_values JSONB,
    reason TEXT,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX content_audit_log_record_idx ON content_audit_log (table_name, record_id);
