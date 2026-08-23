"""Extract plain text from a downloaded scripture PDF, one line per verse (best effort).

Handles two cases:
  - Text-layer PDF (the PDF already contains selectable text): extracted directly, fast, accurate.
  - Scanned/image PDF (no text layer): each page is OCR'd with Tesseract using
    Sanskrit + Hindi trained data. OCR is never perfect, treat the output as a
    draft to review, not final data, per rules.md's "no ungrounded claims" rule.

This does NOT try to detect verse boundaries automatically, it just extracts
text page by page, line by line. You will likely need to manually clean up
line breaks so each line is one verse before running cross_check_texts.py.

Usage:
    python3 scripts/extract_text.py input.pdf output.txt
    python3 scripts/extract_text.py input.pdf output.txt --ocr        # force OCR even if a text layer exists
    python3 scripts/extract_text.py input.pdf output.txt --lang=san+hin  # OCR language(s), default san+hin
"""
import sys

import pypdf


def extract_text_layer(pdf_path):
    reader = pypdf.PdfReader(pdf_path)
    pages = [page.extract_text() or "" for page in reader.pages]
    return pages


def extract_via_ocr(pdf_path, lang):
    import pytesseract
    from pdf2image import convert_from_path

    images = convert_from_path(pdf_path, dpi=300)
    pages = []
    for i, image in enumerate(images):
        print(f"OCR: page {i + 1}/{len(images)}", file=sys.stderr)
        pages.append(pytesseract.image_to_string(image, lang=lang))
    return pages


def has_real_text(pages, min_chars=50):
    return sum(len(p.strip()) for p in pages) >= min_chars


def main(argv):
    if len(argv) < 2:
        print("Usage: python3 extract_text.py input.pdf output.txt [--ocr] [--lang=san+hin]")
        sys.exit(1)

    pdf_path, out_path = argv[0], argv[1]
    force_ocr = "--ocr" in argv
    lang = next((a.split("=", 1)[1] for a in argv if a.startswith("--lang=")), "san+hin")

    pages = [] if force_ocr else extract_text_layer(pdf_path)

    if force_ocr or not has_real_text(pages):
        print("No usable text layer found (or --ocr forced), running OCR...", file=sys.stderr)
        pages = extract_via_ocr(pdf_path, lang)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(pages))

    print(f"Wrote extracted text to {out_path}. Review and split into one-verse-per-line before cross-checking.")


if __name__ == "__main__":
    main(sys.argv[1:])
