-- Renames overloaded/ambiguous column names so meaning is unambiguous:
--   status -> scholar_status (a human decision: pending/approved/rejected/needs_review)
--   confidence -> cross_check_status (source-agreement result only, NOT authenticity: matched/mismatch/not_checked)
-- See rules.md: confidence/matching sources means "sources agree", not "this Sanskrit is correct".

ALTER TABLE verses RENAME COLUMN status TO scholar_status;
ALTER TABLE verses DROP CONSTRAINT verses_status_check;
ALTER TABLE verses ADD CONSTRAINT verses_scholar_status_check
    CHECK (scholar_status IN ('pending', 'approved', 'rejected', 'needs_review'));

ALTER TABLE verses RENAME COLUMN confidence TO cross_check_status;
ALTER TABLE verses DROP CONSTRAINT verses_confidence_check;
ALTER TABLE verses ALTER COLUMN cross_check_status SET DEFAULT 'not_checked';
UPDATE verses SET cross_check_status = 'not_checked' WHERE cross_check_status = 'unverified';
UPDATE verses SET cross_check_status = 'matched' WHERE cross_check_status = 'high_confidence';
ALTER TABLE verses ADD CONSTRAINT verses_cross_check_status_check
    CHECK (cross_check_status IN ('not_checked', 'matched', 'mismatch'));

ALTER TABLE verses ADD COLUMN raw_sanskrit_text TEXT;
COMMENT ON COLUMN verses.sanskrit_text IS 'Comparison/normalized text may diverge from raw_sanskrit_text; sanskrit_text stays the source-of-record verbatim reading.';
COMMENT ON COLUMN verses.raw_sanskrit_text IS 'Unmodified text exactly as extracted, before any normalization applied for cross-checking.';
