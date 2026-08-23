"""Extract raw text from a PDF, per-page, auto-detecting text-layer vs scanned.

Returns a list of page texts, exactly as extracted, never modified. Structure
detection (chapter/verse boundaries) happens separately in structure.py, this
module's only job is: PDF in, raw per-page text out.
"""
import sys

import pypdf


def extract_text_layer(pdf_path):
    reader = pypdf.PdfReader(pdf_path)
    return [page.extract_text() or "" for page in reader.pages]


def extract_via_ocr(pdf_path, lang="san+hin"):
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


def extract_pages(pdf_path, force_ocr=False, ocr_lang="san+hin"):
    """Returns (pages, method) where method is 'text_layer' or 'ocr'."""
    if not force_ocr:
        pages = extract_text_layer(pdf_path)
        if has_real_text(pages):
            return pages, "text_layer"
    return extract_via_ocr(pdf_path, ocr_lang), "ocr"
