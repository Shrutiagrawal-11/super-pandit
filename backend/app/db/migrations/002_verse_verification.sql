-- Adds multi-source cross-check tracking to verses, so scholar review can be
-- fast-tracked for verses independent sources agree on, without skipping
-- review entirely (see rules.md Section 8, PROJECT_PLAN.md Phase 0).

ALTER TABLE verses
    ADD COLUMN confidence TEXT NOT NULL DEFAULT 'unverified'
        CHECK (confidence IN ('unverified', 'high_confidence', 'mismatch')),
    ADD COLUMN cross_check_sources JSONB;
    -- cross_check_sources shape: [{"source": "GRETIL", "text": "...", "match": true}, ...]
