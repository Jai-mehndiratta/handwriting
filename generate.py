from __future__ import annotations

import argparse
import sys
from pathlib import Path

from handwriting import HandwritingBook, parse_markdown

ROOT = Path(__file__).resolve().parent


def find_input() -> Path:
    files = sorted((ROOT / "input").glob("*.md"))
    if not files:
        raise SystemExit(
            "No Markdown file found in input/. Add one (e.g. input/notes.md) and run again."
        )
    if len(files) > 1:
        names = ", ".join(p.name for p in files)
        raise SystemExit(
            f"More than one Markdown file in input/ ({names}). "
            "Pass the file explicitly: python generate.py input/notes.md"
        )
    return files[0]


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Turn Markdown notes into handwritten PDF pages."
    )
    ap.add_argument(
        "markdown",
        nargs="?",
        help="Input Markdown file. If omitted, the single .md file in input/ is used.",
    )
    ap.add_argument(
        "-o",
        "--out",
        help="Output PDF path. Default: output/<markdown-stem>.pdf",
    )
    args = ap.parse_args()

    src = Path(args.markdown) if args.markdown else find_input()
    if not src.exists():
        raise SystemExit(f"Input not found: {src}")
    if src.suffix.lower() not in {".md", ".markdown"}:
        raise SystemExit("Input must be a .md or .markdown file")

    doc = parse_markdown(src)
    out = Path(args.out) if args.out else ROOT / "output" / f"{src.stem}.pdf"
    if not out.is_absolute():
        out = ROOT / out

    book = HandwritingBook()
    book.render(doc, out)
    print(f"Wrote {out} ({len(book.pages)} pages)")


if __name__ == "__main__":
    main()
