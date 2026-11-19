from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Block:
    kind: str
    text: str = ""
    level: int = 0
    rows: list[list[str]] = field(default_factory=list)


@dataclass
class Document:
    metadata: dict[str, str]
    blocks: list[Block]


def _frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    meta: dict[str, str] = {}
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
        if ":" in lines[i]:
            k, v = lines[i].split(":", 1)
            meta[k.strip().lower()] = v.strip()
    if end is None:
        return {}, text
    return meta, "\n".join(lines[end + 1 :])


def parse_markdown(path: str | Path) -> Document:
    raw = Path(path).read_text(encoding="utf-8")
    meta, body = _frontmatter(raw)
    lines = body.splitlines()
    blocks: list[Block] = []
    paragraph: list[str] = []
    in_code = False

    def flush():
        nonlocal paragraph
        if paragraph:
            text = " ".join(x.strip() for x in paragraph).strip()
            if text:
                blocks.append(Block("paragraph", text))
            paragraph = []

    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()
        if stripped.startswith("```"):
            flush()
            in_code = not in_code
            i += 1
            continue
        if in_code:
            i += 1
            continue
        if not stripped:
            flush()
            i += 1
            continue
        if re.fullmatch(r"-{3,}|\*{3,}|_{3,}", stripped):
            flush()
            blocks.append(Block("pagebreak"))
            i += 1
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            flush()
            title = m.group(2).strip()
            if re.match(r"^page\s+\d+", title, re.I):
                blocks.append(Block("pagebreak"))
            else:
                blocks.append(Block("heading", title, level=len(m.group(1))))
            i += 1
            continue
        if stripped.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                row = lines[i].strip()
                if not re.match(r"^\|?[\s:|-]+\|?$", row):
                    cells = [c.strip() for c in row.strip("|").split("|")]
                    rows.append(cells)
                i += 1
            if rows:
                blocks.append(Block("table", rows=rows))
            continue
        m = re.match(r"^([-*+])\s+(.*)$", stripped)
        if m:
            flush()
            blocks.append(Block("bullet", m.group(2).strip(), level=1))
            i += 1
            continue
        m = re.match(r"^(\d+[.)])\s+(.*)$", stripped)
        if m:
            flush()
            blocks.append(Block("numbered", f"{m.group(1)} {m.group(2).strip()}", level=1))
            i += 1
            continue
        if stripped.startswith(">"):
            flush()
            blocks.append(Block("quote", stripped.lstrip(">").strip()))
            i += 1
            continue
        paragraph.append(stripped)
        i += 1
    flush()
    return Document(meta, blocks)
