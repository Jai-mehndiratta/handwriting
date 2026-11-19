from __future__ import annotations

import json
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
GLYPH_JSON = ROOT / "assets" / "glyphs.json"

BLUE_INK = (42, 54, 82, 255)
PENCIL_INK = (64, 64, 68, 205)

TRACK_RATIO = 0.26
SPACE_RATIO = 1.60
CAP_RATIO = 1.50
DIGIT_RATIO = 1.30


class GlyphBook:
    def __init__(self, path: Path = GLYPH_JSON):
        self.meta = json.loads(path.read_text(encoding="utf-8"))
        self.lower = self.meta["lower"]
        self.upper = self.meta["upper"]
        self.digit = self.meta["digit"]
        self.lower_x = float(self.meta["lower_x"])
        self.upper_cap = float(self.meta["upper_cap"])
        self.digit_h = float(self.meta["digit_h"])
        self._cache: dict[str, Image.Image] = {}

    def image(self, g: dict) -> Image.Image:
        path = g["file"]
        if path not in self._cache:
            self._cache[path] = Image.open(ROOT / path).convert("RGBA")
        return self._cache[path]

    def glyph_list(self, ch: str):
        if ch.islower() and ch in self.lower:
            arr = self.lower[ch]
            if ch in "ij":
                arr = arr[:1]  # keep the dotted variant
            return arr, "lower"
        if ch.isupper() and ch in self.upper:
            return self.upper[ch], "upper"
        if ch.isdigit() and ch in self.digit:
            return self.digit[ch], "digit"
        return None, None

    def scale(self, ch: str, kind: str, xh: float) -> float:
        if kind == "lower":
            return xh / self.lower_x
        if kind == "upper":
            return (xh * CAP_RATIO) / self.upper_cap
        return (xh * DIGIT_RATIO) / self.digit_h

    def build(self, text: str, xh: float, seed: int):
        rng = random.Random(seed)
        track = xh * TRACK_RATIO
        items = []
        last: dict[str, int] = {}
        for ch in text:
            arr, kind = self.glyph_list(ch)
            if arr:
                idx = rng.randrange(len(arr))
                if len(arr) > 1 and idx == last.get(ch) and rng.random() < 0.6:
                    idx = (idx + 1) % len(arr)
                last[ch] = idx
                g = arr[idx]
                s = self.scale(ch, kind, xh)
                base = g["advance"] * s
                items.append(
                    {
                        "ch": ch,
                        "g": g,
                        "s": s,
                        "kind": kind,
                        "base": base,
                        "adv": base + track,
                        "dy": rng.uniform(-0.008, 0.008) * xh,
                        "sc": rng.uniform(0.99, 1.01),
                    }
                )
            elif ch == " ":
                items.append({"ch": " ", "base": 0.0, "adv": xh * SPACE_RATIO})
            else:
                base = symbol_width(ch, xh)
                items.append({"ch": ch, "sym": True, "base": base, "adv": base + track})
        return items

    def measure(self, text: str, xh: float) -> float:
        return sum(it["adv"] for it in self.build(text, xh, 1))

    def draw(
        self,
        page: Image.Image,
        draw: ImageDraw.ImageDraw,
        x: float,
        baseline: float,
        text: str,
        xh: float,
        seed: int,
        xscale: float = 1.0,
    ):
        items = self.build(text, xh, seed)
        cx = x
        for it in items:
            if it.get("sym"):
                draw_symbol(draw, it["ch"], cx, baseline, xh)
            elif it.get("g"):
                self._draw_glyph(
                    page,
                    cx,
                    baseline + it["dy"],
                    it["g"],
                    it["s"],
                    it["ch"],
                    it["kind"],
                    it["sc"],
                    xscale,
                )
            cx += it["adv"] * xscale
        return cx - x

    def _draw_glyph(
        self,
        page: Image.Image,
        x: float,
        baseline: float,
        g: dict,
        s: float,
        ch: str,
        kind: str,
        sc: float,
        xscale: float,
    ):
        img = self.image(g)
        w = max(1, int(round(img.width * s * sc * xscale)))
        h = max(1, int(round(img.height * s * sc)))
        im = img.resize((w, h), Image.LANCZOS)
        allow = 0.0
        if kind == "lower" and ch in "agjklpqy":
            allow = max(0, g["top"] + g["inkH"]) * s * sc
        elif kind == "upper" and ch in "QJR":
            allow = max(0, g["top"] + g["inkH"]) * s * sc
        ix = int(round(x - g["pad"] * s * sc * xscale))
        iy = int(round(baseline + allow - (g["h"] - g["pad"]) * s * sc))
        page.alpha_composite(im, (ix, iy))


def symbol_width(ch: str, xh: float) -> float:
    if ch in ".,:;'":
        return xh * 0.16
    if ch == " ":
        return xh * SPACE_RATIO
    if ch in "-=+±×÷&*★→":
        return xh * 0.62
    if ch == "/":
        return xh * 0.5
    if ch in "()[]":
        return xh * 0.34
    if ch == "Δ":
        return xh * 0.62
    if ch == "∵":
        return xh * 0.42
    if ch == "%":
        return xh * 0.62
    return xh * 0.45


def draw_symbol(draw: ImageDraw.ImageDraw, ch: str, x: float, y: float, xh: float):
    lw = max(2, int(round(xh * 0.10)))
    if ch == " ":
        return
    if ch == ".":
        r = max(2, int(xh * 0.07))
        draw.ellipse([x, y - 2 * r, x + 2 * r, y], fill=BLUE_INK)
    elif ch == ",":
        r = max(2, int(xh * 0.065))
        draw.ellipse([x, y - 2 * r, x + 2 * r, y], fill=BLUE_INK)
        draw.line([(x + 1, y - 2), (x - 1, y + int(xh * 0.15))], fill=BLUE_INK, width=lw)
    elif ch == ":":
        r = max(1, int(xh * 0.055))
        draw.ellipse([x, y - 2 * r, x + 2 * r, y], fill=BLUE_INK)
        draw.ellipse(
            [x, y - 2 * r - int(xh * 0.42), x + 2 * r, y - int(xh * 0.42)],
            fill=BLUE_INK,
        )
    elif ch == ";":
        r = max(1, int(xh * 0.055))
        draw.ellipse([x, y - 2 * r, x + 2 * r, y], fill=BLUE_INK)
        draw.ellipse(
            [x, y - 2 * r - int(xh * 0.42), x + 2 * r, y - int(xh * 0.42)],
            fill=BLUE_INK,
        )
        draw.line([(x + 1, y - 2), (x - 1, y + int(xh * 0.15))], fill=BLUE_INK, width=lw)
    elif ch in "'\"":
        draw.line([(x + 2, y - int(xh * 0.75)), (x + 5, y - int(xh * 1.05))], fill=BLUE_INK, width=lw)
        if ch == '"':
            draw.line([(x + 8, y - int(xh * 0.75)), (x + 11, y - int(xh * 1.05))], fill=BLUE_INK, width=lw)
    elif ch == "-":
        draw.line([(x, y - int(xh * 0.43)), (x + int(xh * 0.55), y - int(xh * 0.43))], fill=BLUE_INK, width=lw)
    elif ch == "=":
        for dy in (0.33, 0.62):
            draw.line([(x, y - int(xh * dy)), (x + int(xh * 0.58), y - int(xh * dy))], fill=BLUE_INK, width=lw)
    elif ch in "+±":
        cy = y - int(xh * 0.46)
        arm = int(xh * 0.27)
        draw.line([(x, cy), (x + 2 * arm, cy)], fill=BLUE_INK, width=lw)
        draw.line([(x + arm, cy - arm), (x + arm, cy + arm)], fill=BLUE_INK, width=lw)
        if ch == "±":
            draw.line([(x, y + int(xh * 0.05)), (x + 2 * arm, y + int(xh * 0.05))], fill=BLUE_INK, width=lw)
    elif ch == "/":
        draw.line([(x + 1, y + int(xh * 0.08)), (x + int(xh * 0.42), y - int(xh * 1.15))], fill=BLUE_INK, width=lw)
    elif ch in "()[]":
        box = [x - int(xh * 0.1), y - int(xh * 1.18), x + int(xh * 0.45), y + int(xh * 0.18)]
        if ch in "((":
            draw.arc(box, 70, 290, fill=BLUE_INK, width=lw)
        elif ch in "))":
            draw.arc(box, 250, 110, fill=BLUE_INK, width=lw)
        elif ch == "[":
            draw.line([(x + 4, y - int(xh * 1.15)), (x, y - int(xh * 1.15)), (x, y + int(xh * 0.1)), (x + 4, y + int(xh * 0.1))], fill=BLUE_INK, width=lw)
        else:
            draw.line([(x, y - int(xh * 1.15)), (x + 4, y - int(xh * 1.15)), (x + 4, y + int(xh * 0.1)), (x, y + int(xh * 0.1))], fill=BLUE_INK, width=lw)
    elif ch in "×÷":
        cy = y - int(xh * 0.48)
        arm = int(xh * 0.22)
        draw.line([(x, cy), (x + 2 * arm, cy)], fill=BLUE_INK, width=lw)
        if ch == "×":
            draw.line([(x, cy - arm), (x + 2 * arm, cy + arm)], fill=BLUE_INK, width=lw)
            draw.line([(x, cy + arm), (x + 2 * arm, cy - arm)], fill=BLUE_INK, width=lw)
        else:
            r = max(1, int(xh * 0.04))
            draw.ellipse([x + arm - r, cy - arm - r, x + arm + r, cy - arm + r], fill=BLUE_INK)
            draw.ellipse([x + arm - r, cy + arm - r, x + arm + r, cy + arm + r], fill=BLUE_INK)
    elif ch == "%":
        cy = y - int(xh * 0.55)
        r = max(2, int(xh * 0.06))
        draw.ellipse([x, cy - r, x + 2 * r, cy + r], fill=BLUE_INK)
        draw.ellipse([x + int(xh * 0.35), y - r, x + int(xh * 0.35) + 2 * r, y + r], fill=BLUE_INK)
        draw.line([(x + int(xh * 0.45), cy - int(xh * 0.2)), (x + int(xh * 0.1), y + int(xh * 0.1))], fill=BLUE_INK, width=lw)
    elif ch == "&":
        box = [x, y - int(xh * 0.95), x + int(xh * 0.55), y - int(xh * 0.35)]
        draw.arc(box, 0, 300, fill=BLUE_INK, width=lw)
        draw.line([(x + int(xh * 0.5), y - int(xh * 0.15)), (x, y - int(xh * 0.55))], fill=BLUE_INK, width=lw)
        draw.line([(x, y - int(xh * 0.55)), (x + int(xh * 0.5), y)], fill=BLUE_INK, width=lw)
    elif ch == "→":
        cy = y - int(xh * 0.45)
        draw.line([(x, cy), (x + int(xh * 0.55), cy)], fill=BLUE_INK, width=lw)
        draw.line([(x + int(xh * 0.4), cy - int(xh * 0.15)), (x + int(xh * 0.55), cy)], fill=BLUE_INK, width=lw)
        draw.line([(x + int(xh * 0.4), cy + int(xh * 0.15)), (x + int(xh * 0.55), cy)], fill=BLUE_INK, width=lw)
