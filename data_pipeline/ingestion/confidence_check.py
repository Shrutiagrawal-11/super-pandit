"""Combines OCR confidence, grammar-parse success, and cross-check agreement
into one review_priority per line, per architecture.md 2.5 step 4/6: the
point is directing a scholar's attention to what's actually uncertain, not
computing a correctness score. A verse that's clean on every signal is
'low' priority (shown, pre-checked, still fully re-openable); anything that
fails a signal is 'high'; everything else is 'normal'.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend" / "app"))
from grammar.sandhi_parser import check_parse

OCR_CONFIDENCE_THRESHOLD = 0.85  # below this, treat the line as likely-misread


def compute_priority(cross_check_status, ocr_confidence, grammar_parse_ok):
    """All three inputs may be None/unknown (e.g. no cross-check source
    exists yet, text-layer extraction has no OCR confidence, or the grammar
    parser isn't installed) -- unknown is never treated as a failure, only
    an actual negative signal raises priority.
    """
    if cross_check_status == "mismatch":
        return "high"
    if ocr_confidence is not None and ocr_confidence < OCR_CONFIDENCE_THRESHOLD:
        return "high"
    if grammar_parse_ok is False:
        return "high"

    if cross_check_status == "matched" and grammar_parse_ok is not False:
        return "low"

    return "normal"


def annotate_records(records, ocr_confidences=None):
    """records: list of {chapter, verse, text, ...} from structure.parse_verses.
    ocr_confidences: optional list, same length/order as records, per-line
    OCR confidence (0-1); pass None entries for text-layer lines.
    Adds grammar_parse_ok and review_priority in place; cross_check_status
    is added later by compare.py/write_db.py, so it's read here as whatever
    the caller has already attached (defaults to None = not yet checked).
    """
    ocr_confidences = ocr_confidences or [None] * len(records)
    for rec, ocr_conf in zip(records, ocr_confidences):
        parse_ok = check_parse(rec["text"])
        rec["ocr_confidence"] = ocr_conf
        rec["grammar_parse_ok"] = parse_ok
        rec["review_priority"] = compute_priority(rec.get("cross_check_status"), ocr_conf, parse_ok)
    return records
