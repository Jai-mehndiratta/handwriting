from __future__ import annotations

import io
import math
import random
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw

from .glyphs import BLUE_INK, PENCIL_INK, GlyphBook, symbol_width
from .markdown import Block, Document

ROOT = Path(__file__).resolve().parent.parent
W, H = 3490, 4314
LEFT, RIGHT = 420, 3150
TOP, BOTTOM = 320, 3930

BODY_XH = 38.0
BODY_LINE = 100.0
TABLE_XH = 34.0
TABLE_LINE = 68.0

HEADING = {
    1: (48.0, 112.0),
    2: (42.0, 100.0),
    3: (38.0, 92.0),
    4: (36.0, 88.0),
    5: (34.0, 84.0),
    6: (34.0, 84.0),
}

PENCIL_LINE = 3


def split_text(text: str, limit: int = 1400) -> list[str]:
    """Keep paragraphs small enough to fit a page without clipping."""
    if len(text) <= limit:
        return [text]
    words = text.split()
    chunks, cur = [], ""
    for word in words:
        cand = (cur + " " + word).strip()
        if cur and len(cand) > limit:
            chunks.append(cur)
            cur = word
        else:
            cur = cand
    if cur:
        chunks.append(cur)
    return chunks


class Page:
    def __init__(self, bg: Image.Image, glyphs: GlyphBook):
        self.bg = bg.convert("RGB")
        self.glyphs = glyphs
        self.text = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        self.pencil = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        self.draw = ImageDraw.Draw(self.text)
        self.pdraw = ImageDraw.Draw(self.pencil)
        self.y = float(TOP)

    def rule(self, x1, y1, x2, y2, width=PENCIL_LINE):
        """Mostly straight pencil rule with a slight hand-drawn variation."""
        L = math.hypot(x2 - x1, y2 - y1)
        if L < 1:
            return
        ux, uy = (x2 - x1) / L, (y2 - y1) / L
        nx, ny = -uy, ux
        n = max(4, int(L / 40))
        bow = random.choice((-1, 1)) * random.uniform(0.5, 1.7)
        pts = []
        for i in range(n + 1):
            t = i / n
            off = bow * math.sin(math.pi * t)
            if random.random() < 0.16:
                off += random.uniform(-1.7, 1.7)
            pts.append((x1 + ux * L * t + nx * off, y1 + uy * L * t + ny * off))
        self.pdraw.line(pts, fill=PENCIL_INK, width=max(2, int(width)))
        ghost = []
        for i, (px, py) in enumerate(pts):
            t = i / n
            off = bow * 0.45 * math.sin(math.pi * t) + random.uniform(-0.6, 0.6)
            ghost.append((px + nx * off, py + ny * off))
        self.pdraw.line(ghost, fill=(74, 74, 78, 70), width=max(1, int(width) - 1))

    def wrap(self, text: str, xh: float, width: float) -> list[str]:
        words = text.split()
        lines, cur = [], ""
        for word in words:
            cand = (cur + " " + word).strip()
            if cur and self.glyphs.measure(cand, xh) > width:
                lines.append(cur)
                cur = word
            else:
                cur = cand
        if cur:
            lines.append(cur)
        return lines

    def draw_line(self, x: float, text: str, xh: float):
        # deterministic-ish but varied variants for every line
        seed = random.randrange(1, 2**31 - 1)
        self.glyphs.draw(self.text, self.draw, x, self.y, text, xh, seed)

    def paragraph(self, text: str, xh=BODY_XH, line=BODY_LINE, x=LEFT, width=None,
                  after=36.0, first_indent=0.0):
        width = width or (RIGHT - LEFT)
        lines = self.wrap(text, xh, width)
        if not lines:
            return True
        if self.y + line * len(lines) + after > BOTTOM:
            return False
        for i, ln in enumerate(lines):
            xx = x + (first_indent if i == 0 else 0)
            self.draw_line(xx, ln, xh)
            self.y += line
        self.y += after
        return True

    def heading(self, text: str, level: int):
        xh, line = HEADING.get(level, HEADING[2])
        lines = self.wrap(text, xh, RIGHT - LEFT)
        if self.y + line * len(lines) > BOTTOM:
            return False
        for ln in lines:
            self.draw_line(LEFT, ln, xh)
            self.y += line
        self.y += 24 if level <= 3 else 16
        return True

    def table(self, rows: list[list[str]], force: bool = False):
        if not rows:
            return True
        ncols = max(len(r) for r in rows)
        rows = [r + [""] * (ncols - len(r)) for r in rows]
        xh, line = TABLE_XH, TABLE_LINE

        if ncols <= 3:
            weights = [
                max(8, max(len(r[c]) for r in rows)) for c in range(ncols)
            ]
            total = sum(weights)
            widths = [(RIGHT - LEFT) * w / total for w in weights]
        else:
            weights = [2.8] + [1.0] * (ncols - 1)
            total = sum(weights)
            widths = [(RIGHT - LEFT) * w / total for w in weights]
        xs = [LEFT + sum(widths[:i]) for i in range(ncols + 1)]

        def row_lines(row):
            out = []
            maxn = 1
            for c in range(ncols):
                parts = self.wrap(row[c], xh, widths[c] - 40) if row[c] else [""]
                out.append(parts)
                maxn = max(maxn, len(parts))
            return out, max(52.0, maxn * line + xh + 46)

        header, data = rows[0], rows[1:]
        header_lines, header_h = row_lines(header)
        data_heights = [row_lines(r)[1] for r in data]
        needed = header_h + sum(data_heights)
        if self.y + needed > BOTTOM and not force:
            return False

        def draw_row(row):
            cell_lines, rh = row_lines(row)
            if self.y + rh > BOTTOM:
                return False
            start_y = self.y
            self.rule(LEFT, start_y, LEFT + (RIGHT - LEFT), start_y)
            for ci, lines in enumerate(cell_lines):
                cw = max(1, int(widths[ci]))
                ch = max(1, int(rh))
                cell = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
                inset = 3
                px = int(xs[ci]) + inset
                py = int(self.y) + inset
                crop = self.bg.crop(
                    (px, py, px + max(1, cw - 2 * inset), py + max(1, ch - 2 * inset))
                ).convert("RGBA")
                cell.alpha_composite(crop, (inset, inset))
                cell_draw = ImageDraw.Draw(cell)
                yy = 34 + xh
                for ln in lines:
                    if ln and yy < ch - 6:
                        seed = random.randrange(1, 2**31 - 1)
                        self.glyphs.draw(cell, cell_draw, 14, yy, ln, xh, seed)
                    yy += line
                self.text.alpha_composite(cell, (int(xs[ci]), int(self.y)))
            self.y += rh
            self.rule(LEFT, self.y, LEFT + (RIGHT - LEFT), self.y)
            return True

        if self.y + header_h > BOTTOM:
            return False
        table_top = self.y
        draw_row(header)
        clipped = False
        for row in data:
            if not draw_row(row):
                clipped = True
                break
        for cx in xs:
            self.rule(cx, self.y, cx, table_top, 2)
        return "clipped" if clipped else True


class HandwritingBook:
    def __init__(self):
        self.glyphs = GlyphBook()
        backgrounds = sorted((ROOT / "assets" / "backgrounds").glob("page-*"))
        self.backgrounds = [
            Image.open(p).convert("RGB").resize((W, H), Image.LANCZOS) for p in backgrounds
        ]
        if not self.backgrounds:
            raise RuntimeError("No background pages found in assets/backgrounds")
        self.pages: list[Page] = []
        self.rng = random.Random(20261119)
        self.page: Page | None = None

    def _new_page(self, cover=False):
        bg = self.backgrounds[1] if cover else self.rng.choice(self.backgrounds)
        self.pages.append(Page(bg, self.glyphs))
        self.page = self.pages[-1]
        self.page.y = float(TOP)
        return self.page

    def _next_content_page(self):
        self._new_page()

    def cover(self, meta: dict[str, str]):
        p = self._new_page(cover=True)
        title = meta.get("title", "").strip()
        subtitle = meta.get("subtitle", "").strip()
        y = 760.0
        if title:
            xh = 60.0
            for line in p.wrap(title, xh, RIGHT - LEFT):
                tw = p.glyphs.measure(line, xh)
                p.glyphs.draw(p.text, p.draw, (W - tw) / 2, y, line, xh, 1)
                y += 100
        if subtitle:
            xh = 38.0
            for line in p.wrap(subtitle, xh, RIGHT - LEFT):
                tw = p.glyphs.measure(line, xh)
                p.glyphs.draw(p.text, p.draw, (W - tw) / 2, y, line, xh, 1)
                y += 64
        fields = [
            ("name", "Name"),
            ("roll", "Roll No."),
            ("class", "Class"),
            ("section", "Section"),
            ("subject", "Subject"),
            ("date", "Date"),
        ]
        y = max(1120.0, y + 120)
        for key, label in fields:
            val = meta.get(key, "").strip()
            if val:
                p.glyphs.draw(p.text, p.draw, 760, y, f"{label} - {val}", 38, 1)
                y += 132

    def render(self, doc: Document, out_pdf: Path):
        meta = doc.metadata
        title = meta.get("title", "").strip()
        blocks = list(doc.blocks)
        if not title and blocks and blocks[0].kind == "heading":
            title = blocks[0].text
        cover_ok = meta.get("cover", "true").strip().lower() not in ("false", "no", "0")
        if title and cover_ok:
            self.cover({**meta, "title": title})
            if blocks and blocks[0].kind == "heading" and blocks[0].text == title:
                blocks = blocks[1:]
            self._next_content_page()
        else:
            self._new_page()

        for block in blocks:
            if block.kind == "pagebreak":
                if self.page.y > TOP + 2:
                    self._next_content_page()
                continue
            if block.kind == "heading":
                if self.page.y > BOTTOM - 240 and self.page.y > TOP + 2:
                    self._next_content_page()
                if not self.page.heading(block.text, block.level):
                    self._next_content_page()
                    self.page.heading(block.text, block.level)
            elif block.kind in ("paragraph", "quote"):
                text = block.text
                if block.kind == "quote":
                    text = "“" + text + "”"
                for chunk in split_text(text):
                    while not self.page.paragraph(chunk):
                        self._next_content_page()
            elif block.kind == "bullet":
                while not self.page.paragraph("•  " + block.text, first_indent=20, after=18):
                    self._next_content_page()
            elif block.kind == "numbered":
                while not self.page.paragraph(block.text, first_indent=20, after=18):
                    self._next_content_page()
            elif block.kind == "table":
                # tables get their own attempt, and may split rows across pages
                self._render_table(block.rows)

        self._save_pdf(out_pdf)

    def _render_table(self, rows: list[list[str]]):
        if not rows:
            return
        ok = self.page.table(rows)
        if ok is True:
            return
        if ok is False:
            self._next_content_page()
            ok = self.page.table(rows, force=True)
        if ok == "clipped":
            self._next_content_page()
        else:
            self.page.y += 36

    def _save_pdf(self, out_pdf: Path):
        out_pdf.parent.mkdir(parents=True, exist_ok=True)
        pdf = pymupdf.open()
        for page in self.pages:
            img = page.bg.convert("RGBA")
            img.alpha_composite(page.pencil)
            img.alpha_composite(page.text)
            buf = io.BytesIO()
            img.convert("RGB").save(buf, format="JPEG", quality=88)
            p = pdf.new_page(width=595, height=842)
            p.insert_image(pymupdf.Rect(20, 78, 575, 764), stream=buf.getvalue())
        pdf.set_metadata(
            {
                "title": "Handwritten notes",
                "creator": "handwriting generator",
            }
        )
        pdf.save(out_pdf, deflate=True)
