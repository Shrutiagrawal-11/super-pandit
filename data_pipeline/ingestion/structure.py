"""Detect chapter/verse boundaries in extracted scripture text.

This does NOT guess blindly. It only recognizes a small set of well-documented,
widely-used verse-numbering conventions actually seen in real Sanskrit source
texts (e.g. GRETIL-style "||1.1||", Devanagari double-danda "॥ १-१ ॥", a
bare "1.1" or "1/1" marker at the end of a verse line). If a file's numbering
convention doesn't match any known pattern, this reports that honestly
(zero verses detected, or a warning) rather than silently producing wrong
chapter/verse numbers.

When a new source file's convention isn't recognized, add a new pattern here
explicitly, matched against real examples from that file, not guessed ahead
of time.
"""
import re

# Each pattern must capture (chapter, verse) as its last two groups.
# Ordered by specificity; the first pattern that matches a line's marker wins.
KNOWN_VERSE_MARKERS = [
    # ||2.47||  or  || 2.47 ||   (IAST/GRETIL double-bar style)
    re.compile(r"\|\|\s*(\d+)[.\-](\d+)\s*\|\|"),
    # ॥ २-४७ ॥  or  ॥२४७॥         (Devanagari double-danda, chapter-verse)
    re.compile(r"॥\s*([०-९\d]+)[.\-–]([०-९\d]+)\s*॥"),
    # BG 2.47  /  BhG 2/47
    re.compile(r"Bh?G\s*(\d+)[./](\d+)", re.IGNORECASE),
]

_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


def _to_int(numeral_str):
    return int(numeral_str.translate(_DEVANAGARI_DIGITS))


def detect_marker_pattern(pages):
    """Try each known pattern against the extracted text; return the first
    pattern that finds at least 2 matches (a single coincidental match isn't
    enough evidence the file actually uses that convention)."""
    full_text = "\n".join(pages)
    for pattern in KNOWN_VERSE_MARKERS:
        matches = pattern.findall(full_text)
        if len(matches) >= 2:
            return pattern, len(matches)
    return None, 0


def parse_verses(pages, pattern=None):
    """Splits text into {chapter, verse, text} records using a detected or
    given marker pattern. The verse text is everything since the previous
    marker up to (and not including) the current marker.

    Returns (records, warnings). Does not fabricate chapter/verse numbers for
    text it cannot confidently attribute, unattributable leading text before
    the first marker is reported as a warning, not silently dropped or guessed.
    """
    if pattern is None:
        pattern, count = detect_marker_pattern(pages)
        if pattern is None:
            return [], ["No known verse-numbering convention detected. "
                        "Inspect the file manually and add a new pattern to "
                        "KNOWN_VERSE_MARKERS rather than guessing."]

    full_text = "\n".join(pages)
    warnings = []
    records = []

    matches = list(pattern.finditer(full_text))
    if matches and matches[0].start() > 0:
        leading = full_text[: matches[0].start()].strip()
        if leading:
            warnings.append(f"Text before the first detected verse marker was not attributed to any verse ({len(leading)} chars).")

    for i, m in enumerate(matches):
        chapter = _to_int(m.group(1))
        verse = _to_int(m.group(2))
        text_start = matches[i - 1].end() if i > 0 else 0
        text = full_text[text_start:m.start()].strip()
        if not text:
            warnings.append(f"Verse marker for {chapter}.{verse} found with no preceding text, likely a parsing issue.")
            continue
        records.append({"chapter": chapter, "verse": verse, "text": text})

    return records, warnings
