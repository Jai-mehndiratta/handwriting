# Visual / layout notes

These are the rules that produced the approved handwritten PDF. They are encoded in `handwriting/render.py` and `handwriting/glyphs.py`.

## Canvas

- 3490 × 4314 image pages, placed on A4 in the output PDF.
- Use the three original blank-page photos in `assets/backgrounds/` unchanged. Do not clean or replace the paper texture.
- Keep all writing inside the printed inner frame.
- Hard-stop content at the frame bottom rather than writing outside it.

## Writing

- Blue pen: glyph images are used in their original blue ink.
- Body x-height: 38 px; body line spacing: 100 px.
- Heading sizes: H1 48, H2 42, H3 38; keep a heading with some following content.
- Letter spacing ratio: 0.26 of x-height; word spacing: 1.6 of x-height.
- Randomise among the supplied variants per character, with tiny baseline/size jitter.
- Use a cover page with name / roll / section metadata when front matter is supplied.
- No page numbers. No decorative horizontal rules.

## Tables

- Table text: 34 px; row line spacing: 68 px.
- Real hand-drawn pencil grids only for tables.
- Pencil rules: mostly straight, small mid-line bow, occasional 1–2 px hand wobble.
- Render each cell on its own small tile:
  - crop the underlying paper into the tile,
  - draw blue table text inside the tile,
  - paste the tile back.
- This masks any pencil line behind the cell text; the pencil remains at the cell borders.
- Cell top padding: 34 px; cell inset: 3 px; label columns get extra width.
- If a table does not fit, start a new page. If it is taller than a page, stop at the frame rather than spilling.

## Pagination

- `---` or `## Page N` starts a new page.
- Tables start on a fresh page if the whole table does not fit.
- Avoid orphan headings at the bottom of a page.
- Paragraphs are split into safe chunks before layout.

## Output

- A4 portrait, images inserted with a 20/78/575/764 pt rectangle.
- JPEG quality 88.
- Source Markdown remains the single source of truth.
