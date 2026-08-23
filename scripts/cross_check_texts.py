"""Cross-check scripture sources by (chapter, verse) and flag mismatches.

Runs locally, no LLM/API calls, free to re-run. It does NOT judge whether a
flagged mismatch is a real textual variant or just transliteration noise,
that judgment stays with a human or a targeted spot-check, per rules.md's
"no guessing" rule.

A "matched" result means the sources being compared agree, NOT that the
Sanskrit is authentically correct, see rules.md for why those are kept as
separate fields (cross_check_status vs scholar_status).

Input format: each source is a JSON file, a list of records:
    [{"chapter": 1, "verse": 1, "text": "..."}, ...]
You are responsible for parsing your downloaded book into this shape first
(e.g. via extract_text.py plus manual/scripted chapter:verse tagging).
Verses are matched by (chapter, verse), never by line position, so extra,
missing, or reordered verses in one source don't corrupt every verse after them.

Usage:
    python3 scripts/cross_check_texts.py primary.json secondary1.json [secondary2.json ...]

Output: prints one line per (chapter, verse) present in the primary source:
matched / mismatch / not_checked (verse absent from a secondary source).
"""
import json
import sys
import unicodedata


def normalize(text):
    # Comparison-only view. The raw text is never modified or discarded,
    # this normalization exists solely to ignore whitespace/punctuation-style
    # noise, not to decide what the "real" reading is.
    text = unicodedata.normalize("NFC", text.strip())
    for ch in "|.॥।,;:":
        text = text.replace(ch, "")
    return " ".join(text.split())


def load_source(path):
    with open(path, encoding="utf-8") as f:
        records = json.load(f)
    return {(r["chapter"], r["verse"]): r["text"] for r in records}


def main(paths):
    primary_path, *secondary_paths = paths
    primary = load_source(primary_path)
    secondaries = [(p, load_source(p)) for p in secondary_paths]

    counts = {"matched": 0, "mismatch": 0, "not_checked": 0}
    for (chapter, verse), raw_text in sorted(primary.items()):
        primary_norm = normalize(raw_text)
        checks = []
        for path, lookup in secondaries:
            other_raw = lookup.get((chapter, verse))
            if other_raw is None:
                checks.append((path, None, None))
            else:
                checks.append((path, other_raw, normalize(other_raw) == primary_norm))

        if any(c[2] is None for c in checks):
            status = "not_checked"
        elif all(c[2] for c in checks):
            status = "matched"
        else:
            status = "mismatch"
        counts[status] += 1

        label = f"{chapter}.{verse}"
        if status == "matched":
            print(f"[{label}] matched")
        elif status == "not_checked":
            missing = [p for p, t, m in checks if t is None]
            print(f"[{label}] not_checked (missing from: {', '.join(missing)})")
        else:
            print(f"[{label}] MISMATCH")
            print(f"    primary ({primary_path}): {raw_text}")
            for path, other_raw, ok in checks:
                if ok is False:
                    print(f"    differs  ({path}): {other_raw}")

    total = sum(counts.values())
    print(f"\n{total} verses checked: {counts['matched']} matched, "
          f"{counts['mismatch']} mismatch, {counts['not_checked']} not_checked.")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 cross_check_texts.py primary.json secondary1.json [secondary2.json ...]")
        sys.exit(1)
    main(sys.argv[1:])
