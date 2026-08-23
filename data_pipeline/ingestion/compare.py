"""Compare a primary source's verses against one or more cross-check sources
by (chapter, verse) identity, never by line position.

A 'matched' result means the sources agree, it does NOT mean the Sanskrit is
authentically correct, that judgment belongs to a scholar. See rules.md.

Comparison strategy: convert everything to Devanagari before comparing, never
compare across scripts directly. Our primary source (GRETIL) is strict IAST;
some cross-check sources are already Devanagari, others use looser Roman
conventions (e.g. "sh"/"ch" digraphs instead of "ś"/"c"). A looser convention
is not valid strict IAST, so it is NOT run through the IAST converter, doing
so silently misparses it into wrong Devanagari (confirmed by direct testing:
"niśhcharati" parsed as strict IAST produces "निश्ह्छरति", not the correct
"निश्चरति") which would produce false mismatches, exactly the wrong kind of
error for a project whose entire premise is not asserting things that aren't
verified. Text already in Devanagari is used as-is; text in strict IAST is
converted; anything else is left for a human to align, not guessed at.
"""
import re
import unicodedata

from indic_transliteration import sanscript
from indic_transliteration.sanscript import SchemeMap, SCHEMES

_IAST_TO_DEVANAGARI = SchemeMap(SCHEMES[sanscript.IAST], SCHEMES[sanscript.DEVANAGARI])

_DEVANAGARI_RE = re.compile(r"[ऀ-ॿ]")
_STRICT_IAST_RE = re.compile(r"[āīūṛṝḷḹṃḥñṅṇṭḍśṣ]")  # a strict-IAST-only diacritic present means it's safe to convert


def is_devanagari(text):
    return bool(_DEVANAGARI_RE.search(text))


def is_strict_iast(text):
    """Heuristic, not a guarantee: strict IAST is distinguished from a loose
    Roman convention by its diacritics (ā, ś, ñ, ...). A verse with none of
    these diacritics (rare, but possible for a short/simple line) can't be
    told apart from loose romanization this way, and is left unconverted
    rather than risk a wrong guess.
    """
    return bool(_STRICT_IAST_RE.search(text.lower()))


def to_devanagari_or_none(text):
    """Returns Devanagari text, or None if this text isn't safely convertible
    (i.e. it's neither already Devanagari nor confidently strict IAST). None
    means: don't compare this one automatically, a human needs to align it.
    """
    if is_devanagari(text):
        return text
    if is_strict_iast(text):
        # ṁ (candrabindu-style anusvara) and ṃ (anusvara dot) are the same
        # sound but map to two different Devanagari characters unless folded
        # to one first.
        return sanscript.transliterate(text.replace("ṁ", "ṃ"), scheme_map=_IAST_TO_DEVANAGARI)
    return None


_AVAGRAHA_OR_APOSTROPHE = "ऽ'’"

# Some sources prepend a speaker-attribution line to a verse's stored text
# ("अर्जुन उवाच" / "संजय उवाच" / "धृतराष्ट्र उवाच", "X said"), others store it
# separately from the verse proper. This is a real structural difference in
# what's stored, not noise, so it's detected and reported explicitly
# (speaker_line diff_reason) rather than silently stripped alongside
# punctuation, where it would look identical to every other kind of mismatch.
#
# "उवाच" doesn't always appear as a literal substring: "भगवान् उवाच" commonly
# sandhi-joins to "भगवानुवाच" (न् + उ -> नु), so the regex matches either the
# separate word "उवाच" or a word ending in "नुवाच"/"दुवाच" (the sandhi-joined
# forms after a word ending in न् or द्, the two cases this corpus contains).
_SPEAKER_LINE_RE = re.compile(r"^[^।॥]{1,25}(?:\bउवाच|[नद]ुवाच)[।\s]*")


def strip_leading_speaker_line(devanagari_text):
    return _SPEAKER_LINE_RE.sub("", devanagari_text.strip(), count=1)


_VIRAMA = "्"


def normalize(devanagari_text, strip_avagraha=False):
    """devanagari_text must already be Devanagari (see to_devanagari_or_none).
    NFKC normalization first, so visually-identical characters with different
    underlying byte sequences (precomposed vs. combining-mark sequences)
    compare equal rather than falsely differing.
    """
    text = unicodedata.normalize("NFKC", devanagari_text.strip())
    text = re.sub(r"[।॥]\s*[०-९\d]+(?:[.\-‑][०-९\d]+)?\s*[।॥]?", "", text)  # verse-number marker, either digit system
    text = re.sub(r"[०-९\d]", "", text)  # any other bare digits
    text = re.sub(r"[।॥,;:.\-]", "", text)
    if strip_avagraha:
        text = "".join(ch for ch in text if ch not in _AVAGRAHA_OR_APOSTROPHE)
    else:
        text = text.replace("’", "'")  # fold the two apostrophe variants, keep avagraha itself distinct
    # NOTE: a word-final consonant is sometimes written with an explicit
    # virama before a space ("उद्धरेद् ...") and sometimes without ("उद्धरेद
    # ..."), or a word may be sandhi-joined directly with no space at all
    # where another source inserts one. An earlier attempt to fold this away
    # by stripping any virama before a following consonant was reverted: it
    # risks silently equating a genuine conjunct-consonant spelling error
    # (e.g. क्ष vs. कष, a real, different letter) with a correct one, which
    # would hide an actual mistake, worse than an over-cautious mismatch flag.
    # A verse that differs only in this specific rendering convention will
    # show as a mismatch and go to scholar review rather than being silently
    # resolved, the same disclosed tradeoff already accepted for the
    # "hy ātmano" vs "hyātmano" case (see PROJECT_PLAN.md Phase 0 notes).
    return re.sub(r"\s+", "", text)


def texts_equal(a_devanagari, b_devanagari):
    """Returns (equal, diff_reason). diff_reason is None on a strict match,
    otherwise one of:
      "avagraha" - differ only in avagraha/apostrophe presence (some digital
                   editions simply omit ऽ).
      "speaker_line" - differ only in whether a leading speaker-attribution
                        line ("श्री भगवानुवाच" etc.) is included.
    Either case is treated as a soft match (equal=True) for cross_check_status
    purposes, since the underlying verse content agrees, but the reason is
    still returned so it can be shown to a scholar rather than hidden.
    """
    strict_equal = normalize(a_devanagari) == normalize(b_devanagari)
    if strict_equal:
        return True, None

    avagraha_equal = normalize(a_devanagari, strip_avagraha=True) == normalize(b_devanagari, strip_avagraha=True)
    if avagraha_equal:
        return True, "avagraha"

    a_no_speaker = strip_leading_speaker_line(a_devanagari)
    b_no_speaker = strip_leading_speaker_line(b_devanagari)
    if (a_no_speaker != a_devanagari or b_no_speaker != b_devanagari) and normalize(a_no_speaker) == normalize(b_no_speaker):
        return True, "speaker_line"

    return False, None


def compare_verses(primary_records, cross_check_sources):
    """primary_records: list of {chapter, verse, text}.
    cross_check_sources: list of (source_name, records) tuples.

    Returns a list of {chapter, verse, primary_text, cross_check_status, readings}
    where readings is a list of {source, text, matches, diff_reason, unconverted}.
    matches is None if the verse wasn't found in that source, or if either
    side's script/convention couldn't be safely converted to Devanagari
    (flagged via unconverted=True, not silently skipped). diff_reason is set
    (see texts_equal) when matches is True but a soft, explainable difference
    (avagraha presence, a leading speaker-attribution line) was found, so a
    scholar sees why it wasn't a byte-for-byte match even though it counts as
    agreement here.
    """
    lookups = [(name, {(r["chapter"], r["verse"]): r["text"] for r in records})
               for name, records in cross_check_sources]

    results = []
    for rec in primary_records:
        key = (rec["chapter"], rec["verse"])
        primary_deva = to_devanagari_or_none(rec["text"])
        readings = []
        for name, lookup in lookups:
            other_text = lookup.get(key)
            if other_text is None:
                readings.append({"source": name, "text": None, "matches": None, "diff_reason": None, "unconverted": False})
                continue

            other_deva = to_devanagari_or_none(other_text)
            if primary_deva is None or other_deva is None:
                # Can't safely convert one side, don't guess: surface it for a human.
                readings.append({"source": name, "text": other_text, "matches": None, "diff_reason": None, "unconverted": True})
                continue

            equal, diff_reason = texts_equal(primary_deva, other_deva)
            readings.append({"source": name, "text": other_text, "matches": equal, "diff_reason": diff_reason, "unconverted": False})

        if any(r["matches"] is None for r in readings):
            status = "not_checked"
        elif all(r["matches"] for r in readings):
            status = "matched"
        else:
            status = "mismatch"

        results.append({
            "chapter": rec["chapter"],
            "verse": rec["verse"],
            "primary_text": rec["text"],
            "cross_check_status": status,
            "readings": readings,
        })
    return results
