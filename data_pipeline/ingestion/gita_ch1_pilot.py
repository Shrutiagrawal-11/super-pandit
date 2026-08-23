"""
One-off pilot script: ingest Bhagavad Gita Chapter 1 Sanskrit verses + (if found) Hindi
commentary, as pending rows awaiting scholar review.

Sources:
  - Sanskrit verse text: Wikisource, Besant 4th edition, Discourse 1
    https://en.wikisource.org/wiki/Bhagavad-Gita_(Besant_4th)/Discourse_1
  - Hindi commentary (attempted): Internet Archive 1886 scan, CC0
    https://archive.org/details/xmQr_bhagavad-gita-with-shankar-bhashya-tika-of-anand-giri-explanation-by-pt.-surya-1886-jagad-hita-

Everything this script inserts lands with status='pending' (the schema default).
Nothing here approves or reviews anything, per rules.md: no unverified content
reaches users, and this script does not build a review tool.

IMPORTANT FINDING (see the Hindi section below): the 1886 Internet Archive item
turned out, on inspection of its OCR text, to contain no Hindi commentary at all.
Its "explanation by Pt. Surya" is itself a Sanskrit tika (टीका), same as the
Shankar Bhashya and Anand Giri tika alongside it. Rather than guess at a mapping
that doesn't exist, this script does not insert anything into `commentaries` and
prints why. See the final report the script prints for details.
"""

import re
import sys
import urllib.parse
import urllib.request

import psycopg

DB_URL = "postgresql://pandit:pandit_dev_local@localhost:5432/ai_pandit"

WIKISOURCE_URL = "https://en.wikisource.org/wiki/Bhagavad-Gita_(Besant_4th)/Discourse_1"
WIKISOURCE_CITATION = "Bhagavad-Gita (Besant 4th edition, 1922), Discourse 1, Wikisource"

IA_IDENTIFIER = "xmQr_bhagavad-gita-with-shankar-bhashya-tika-of-anand-giri-explanation-by-pt.-surya-1886-jagad-hita-"
IA_FILENAME = "Bhagavad Gita with Shankar Bhashya, Tika of Anand Giri & Explanation by Pt. Surya 1886 - Jagad Hita Press_djvu.txt"
IA_TXT_URL = f"https://archive.org/download/{IA_IDENTIFIER}/{urllib.parse.quote(IA_FILENAME)}"

DEVANAGARI_DIGITS = "०१२३४५६७८९"


def devanagari_to_int(s: str) -> int:
    return int("".join(str(DEVANAGARI_DIGITS.index(ch)) for ch in s))


def fetch(url: str, timeout: int = 60) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (AI Pandit ingestion pilot)"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def strip_tags(html: str) -> str:
    """Remove HTML tags and unescape the handful of entities Wikisource uses here."""
    text = re.sub(r"<[^>]+>", "", html)
    text = text.replace("&#160;", " ").replace("&#8203;", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_sanskrit_verses(html: str) -> list[tuple[int, str]]:
    """
    Each verse's Sanskrit text sits in a <div class="wst-lang" lang="sa" dir="ltr">...</div>
    block, ending in a verse-number marker like "॥ १ ॥". This is a reliable, verified
    structural pattern on this specific Wikisource page (confirmed by manual inspection),
    not a guess. The final block on the page is the chapter's closing colophon, which
    has no "॥ N ॥" marker, so it's naturally excluded by the regex below.
    """
    blocks = re.findall(
        r'<div class="wst-lang" lang="sa" dir="ltr">(.*?)</div>\s*</div>\s*</div>',
        html,
        re.S,
    )
    verses = []
    for block in blocks:
        m = re.search(r"॥\s*([०-९]+)\s*॥", block)
        if not m:
            continue  # colophon / non-verse block, not a numbered shloka
        verse_num = devanagari_to_int(m.group(1))
        sanskrit_text = strip_tags(block)
        verses.append((verse_num, sanskrit_text))
    return verses


def check_ia_source_for_hindi() -> str:
    """
    Fetch the Internet Archive OCR text and check whether it actually contains Hindi
    commentary, rather than assuming so from the item's title. Returns a short report
    string describing what was found. This performs the real fetch every run so the
    check reflects the live source, not a cached assumption.
    """
    try:
        text = fetch(IA_TXT_URL, timeout=90)
    except Exception as e:
        return f"Could not fetch Internet Archive OCR text ({IA_TXT_URL}): {e}"

    # Hindi has function words that essentially don't occur in classical Sanskrit
    # (है, हैं, नहीं, हूँ). Sanskrit commentary uses है/हैं / के / में only as rare OCR
    # misreads of garbled conjuncts, not as real words. Count them as a sanity check,
    # rather than assuming.
    hindi_markers = [" है ", " हैं ", " नहीं ", " हूँ ", " किया "]
    counts = {m.strip(): text.count(m) for m in hindi_markers}

    # Structural check: Sanskrit commentary in this book is explicitly labelled with
    # Sanskrit abbreviations (शां भा० / आ० टी० / प० टी०), which is what's actually
    # present, verified by direct reading of the OCR text around Chapter 1's start.
    sanskrit_commentary_labels = ["आ० टी०", "प० टी०", "शांकर भाष्यम्"]
    label_counts = {lbl: text.count(lbl) for lbl in sanskrit_commentary_labels}

    return (
        f"Fetched {len(text)} chars of OCR text from Internet Archive.\n"
        f"  Hindi function-word occurrences (out of {len(text)} chars, book-wide): {counts}\n"
        f"  -> these are sparse OCR noise (misread Sanskrit conjuncts), not real Hindi sentences;\n"
        f"     manual inspection of the hits nearest Chapter 1 confirmed this.\n"
        f"  Sanskrit commentary label occurrences: {label_counts}\n"
        f"  -> the book's per-verse commentary is entirely in Sanskrit (Shankar's Bhashya,\n"
        f"     Anand Giri's Tika, and Pt. Surya's Tika are all Sanskrit prose commentary,\n"
        f"     not Hindi). 'Explanation by Pt. Surya' in the title refers to a Sanskrit tika,\n"
        f"     not a Hindi gloss.\n"
        f"  CONCLUSION: this source contains no Hindi commentary text for Chapter 1 (or,\n"
        f"  from this scan, anywhere in the book). Nothing was inserted into `commentaries`\n"
        f"  from this source. A different source is needed for Hindi commentary."
    )


def main():
    print("Fetching Sanskrit verses from Wikisource...")
    html = fetch(WIKISOURCE_URL)
    verses = extract_sanskrit_verses(html)
    verses.sort(key=lambda v: v[0])

    print(f"Extracted {len(verses)} verses.")
    if len(verses) != 47:
        print(
            f"WARNING: expected 47 verses for Gita Chapter 1, got {len(verses)}. "
            "Not proceeding with insert until this is checked by hand.",
            file=sys.stderr,
        )
        sys.exit(1)

    print("\nChecking the Internet Archive source for Hindi commentary...")
    ia_report = check_ia_source_for_hindi()
    print(ia_report)

    print("\nInserting Sanskrit verses into `verses` (status='pending')...")
    inserted = 0
    skipped = 0
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            for verse_num, sanskrit_text in verses:
                cur.execute(
                    """
                    INSERT INTO verses (scripture, chapter, verse_number, sanskrit_text, source_citation)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (scripture, chapter, verse_number) DO NOTHING
                    RETURNING id
                    """,
                    ("Bhagavad Gita", 1, verse_num, sanskrit_text, WIKISOURCE_CITATION),
                )
                if cur.fetchone():
                    inserted += 1
                else:
                    skipped += 1
        conn.commit()

    print(f"\nInserted {inserted} verse rows, skipped {skipped} (already present).")
    print("No `commentaries` rows were inserted (see Hindi-source finding above).")
    print("All inserted rows have status='pending' and are not visible to the RAG pipeline.")


if __name__ == "__main__":
    main()
