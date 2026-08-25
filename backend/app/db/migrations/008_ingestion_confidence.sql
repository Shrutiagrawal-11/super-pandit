-- Phase 7: confidence-flagging for the automated ingestion pipeline, so
-- scholar review can be prioritized (low-confidence lines shown by default)
-- rather than requiring every line to be re-read from scratch, per
-- architecture.md 2.5 step 6-7. Derived from OCR confidence + grammar-parse
-- success + the existing cross_check_status; never itself a pass/fail
-- verdict, that stays the scholar's call.

ALTER TABLE verses
    ADD COLUMN IF NOT EXISTS ocr_confidence NUMERIC,       -- 0-1, NULL if extracted from a clean text layer (no OCR involved)
    ADD COLUMN IF NOT EXISTS grammar_parse_ok BOOLEAN,      -- NULL = not yet checked; see sandhi_parser.py
    ADD COLUMN IF NOT EXISTS review_priority TEXT NOT NULL DEFAULT 'normal'
        CHECK (review_priority IN ('low', 'normal', 'high'));
