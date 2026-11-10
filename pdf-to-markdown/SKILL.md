---
name: pdf-to-markdown
description: Convert PDF files to Markdown with a script that keeps the document structure (headings, lists, tables, bold/italic, reading order, multi-column layout) and OCRs scanned pages. Use when asked to convert, transform or export a PDF to Markdown/.md, to make a PDF readable or indexable for an LLM/RAG, or "converter PDF para Markdown". Not for merging, splitting, filling or annotating PDFs.
---

# PDF to Markdown

Converts PDF → Markdown via `scripts/pdf2md.sh`, built on
[PyMuPDF4LLM](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/) with the
PyMuPDF Layout engine. The script does the extraction; your job is choosing
the options and checking the result.

What it preserves:

- Headings (`#`..`######`) inferred from font size/weight and layout.
- Bulleted and numbered lists, bold, italic, monospace/code blocks.
- Tables as GitHub Markdown tables (or HTML with `--html-tables`).
- Reading order across multi-column pages.
- Cleaned by default (each has a `--keep-*` flag to opt out):
  - running headers/footers — lines repeated at the top/bottom of ≥30% of
    pages, e.g. `© ISO 2018 – All rights reserved` — and lone page numbers;
  - dot-leader tables of contents (`1 Scope ........ 1`), which the extractor
    turns into broken tables; `--toc` rebuilds a linked one from headings.
- Images written as `<name>_assets/<name>-p0019-13.png` (page 19, image 13).

## Run

```bash
~/.claude/skills/pdf-to-markdown/scripts/pdf2md.sh documento.pdf
# -> documento.md next to the PDF
```

The wrapper creates a pinned virtualenv in
`~/.cache/pdf-to-markdown/venv` on first run (needs `python3` and network
once). Override with `PDF2MD_VENV=/path`. Never install into the skills repo.

| Need | Flags |
| --- | --- |
| Choose output file / dir | `-o out.md` or `-o outdir/` |
| Folder of PDFs | `pdf2md.sh pasta/ -o md/ [-r]` |
| Subset of pages (1-based) | `--pages "1-5,8,20-"` |
| Keep figures | `--images write` (→ `<name>_assets/`, relative links) or `--images embed` (base64) |
| Scanned PDF | default `--ocr auto` OCRs pages without text; `--ocr force` for every page; `--lang por+eng` |
| Born-digital, faster | `--ocr off` |
| Tables with merged cells | `--html-tables` |
| Standards, specs, laws, theses (numbered clauses) | `--number-headings` |
| Linked table of contents | `--toc` (replaces the PDF's own TOC heading, or goes on top) |
| Keep headers/footers / page numbers | `--keep-headers` |
| Keep the PDF's dot-leader TOC | `--keep-toc` |
| Page boundaries / citations | `--page-separators` (`<!-- page N -->`, invisible when rendered) |
| Encrypted PDF | `--password ...` |

Stdout reports one line per file: pages, headings, tables, characters,
dot-leader TOC rows removed, and pages that had no text layer. Exit code is
`0` on success, `1` if any file failed (the batch continues), `66` when no
input is found.

## Workflow

1. Run the script with defaults first. Add `--images write` if the document
   has figures/diagrams the user cares about.
2. Read the stats line, then spot-check the `.md`:
   - **Numbered document** (`1 Scope`, `5.2.1 …`, `Annex A`) with headings
     at odd levels (clause 1 at `####`) → re-run with `--number-headings`
     (plus `--toc` if the PDF had a contents page). It sets the level from
     the number (`1` → `##`, `5.2` → `###`, `A.2.1` → `####`), rejoins a
     number split from its title (`3.1.1` / `acquirer`), merges
     `Annex A (normative)` with its title, turns `Figure N —` / `Table N —`
     captions into bold text and `a)` items back into list items.
   - **0 headings** on a structured document → headings are probably
     styled only by bold text; tell the user, don't invent heading levels.
   - **Footer text still present** → it repeats on fewer than 30% of pages
     or sits mid-page; mention it rather than editing by hand.
   - **0 tables** where the PDF clearly has tables → retry with
     `--html-tables`; borderless tables may come out as plain text.
   - **"pages without text layer"** → those pages were OCRed. Check that
     text for garbled words (accents, `ç`, `ã`). If tesseract lacks
     Portuguese (`tesseract --list-langs` has no `por`), say so and suggest
     installing `tesseract-data-por` (Arch) / `tesseract-ocr-por` (Debian);
     the script auto-selects `por+eng` once it is present.
3. Report the output path and anything that did not convert cleanly. Do
   not hand-edit the Markdown unless the user asks; fix by changing flags.

## Limits

- Math formulas come out as text, not LaTeX.
- Without `--number-headings`, heading levels come from font size: the
  same visual style always maps to the same level, but the absolute level
  may differ from the source outline.
- Footer text glued onto a body line (no line break in the PDF) stays.
- `--toc` anchors follow MkDocs/Python-Markdown slugs; other renderers
  may slug some punctuation (`—`) differently.
- Forms, annotations and digital signatures are not converted.
- Very large PDFs: convert in `--pages` ranges and concatenate, or use
  `--page-separators` so each page can be located later.
