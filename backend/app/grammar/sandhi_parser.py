"""Sanskrit grammar-parse check, per architecture.md 2.5 step 4: a line that
fails to produce any valid sandhi-split usually signals an extraction error
(a misread character), not unusual grammar -- classical verses are
grammatically well-formed by construction. This is used as a confidence
signal for the ingestion pipeline (Phase 7), never as a pass/fail gate on
its own: a failed parse raises review priority, it never blocks or auto-
rejects a verse, that judgment stays the scholar's.
"""
import logging

try:
    from sanskrit_parser import Parser

    _parser = Parser(output_encoding="devanagari")
    AVAILABLE = True
except Exception:
    # Not installed, or failed to initialize (missing data files, etc).
    # Ingestion still works without it -- grammar_parse_ok just stays NULL
    # and review_priority falls back to OCR confidence + cross-check status
    # alone, per architecture.md's "flag what's uncertain" approach, not an
    # all-or-nothing dependency.
    _parser = None
    AVAILABLE = False


def check_parse(devanagari_line):
    """Returns True (parsed), False (no valid split found), or None (parser
    unavailable / this line couldn't be checked -- callers must treat None
    as 'unknown', never as a failure).
    """
    if _parser is None:
        return None
    try:
        # sanskrit_parser calls logging.basicConfig(level=DEBUG) internally
        # and re-asserts it on each call, so disabling this only at import
        # time doesn't stick -- logging.disable() overrides every logger
        # regardless, so it's the only reliable way to keep ingestion's
        # console output readable across many lines checked.
        logging.disable(logging.WARNING)
        splits = _parser.split(devanagari_line, limit=1)
        return bool(splits)
    except Exception:
        # A parser exception on a single malformed/unusual line shouldn't
        # crash the ingestion batch; treat it the same as "unknown".
        return None
    finally:
        logging.disable(logging.NOTSET)
