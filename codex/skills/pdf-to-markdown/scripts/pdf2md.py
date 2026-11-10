#!/usr/bin/env python3
"""Convert PDF files to structure-preserving Markdown with pymupdf4llm.

Run through pdf2md.sh, which provides a virtualenv with pinned dependencies.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pymupdf
import pymupdf4llm


def parse_pages(spec: str, page_count: int) -> list[int]:
    """Turn a 1-based spec like "1-3,7,10-" into 0-based page indices."""
    pages: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, hi = part.split("-", 1)
            start = int(lo) if lo else 1
            end = int(hi) if hi else page_count
        else:
            start = end = int(part)
        if start < 1 or end > page_count or start > end:
            raise ValueError(f"page range {part!r} outside 1-{page_count}")
        pages.extend(range(start - 1, end))
    return sorted(set(pages))


def default_ocr_language() -> str:
    """Prefer Portuguese + English when the tesseract data is installed."""
    if not shutil.which("tesseract"):
        return "eng"
    try:
        out = subprocess.run(
            ["tesseract", "--list-langs"], capture_output=True, text=True, check=False
        ).stdout.split()
    except OSError:
        return "eng"
    langs = [lang for lang in ("por", "eng") if lang in out]
    return "+".join(langs) or "eng"


def collect_inputs(paths: list[Path], recursive: bool) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            pattern = "**/*.pdf" if recursive else "*.pdf"
            files.extend(sorted(p for p in path.glob(pattern) if p.is_file()))
        elif path.is_file():
            files.append(path)
        else:
            raise FileNotFoundError(path)
    return files


def output_path(src: Path, args: argparse.Namespace, many: bool) -> Path:
    if args.output is None:
        return src.with_suffix(".md")
    if many or args.output.is_dir() or args.output.suffix.lower() != ".md":
        return args.output / f"{src.stem}.md"
    return args.output


PAGE_SEP = re.compile(r"^--- end of page\.page_number=(\d+) ---$", re.M)
DOT_LEADER = re.compile(r"(?:\.\s?){5,}|…{3,}")
PAGE_NUMBER = re.compile(r"^(?:[->]\s*)?(?:\*\*)?(?:[0-9]{1,4}|[ivxlc]{1,6})(?:\*\*)?$", re.I)


def split_pages(md: str) -> tuple[list[str], list[str]]:
    """Split on the extractor's page separators: (page bodies, page numbers)."""
    parts = PAGE_SEP.split(md)
    bodies, numbers = parts[0::2], parts[1::2]
    if len(bodies) > len(numbers) and not bodies[-1].strip():
        bodies.pop()
    return bodies, numbers


def furniture_key(line: str) -> str:
    """Normalize a line so the same header/footer matches on every page."""
    key = re.sub(r"^(?:[->]\s*|#+\s*)+", "", line.strip())
    key = re.sub(r"[*_`]", "", key)
    key = re.sub(r"[0-9]+|\b[ivxlc]{1,6}\b", "#", key, flags=re.I)
    return re.sub(r"\s+", " ", key).strip()


EDGE_LINES = 4  # headers/footers live in the first/last few lines of a page


def edge_indices(lines: list[str]) -> list[int]:
    content = [i for i, l in enumerate(lines) if l.strip()]
    return sorted(set(content[:EDGE_LINES] + content[-EDGE_LINES:]))


def strip_page_furniture(bodies: list[str]) -> list[str]:
    """Drop running headers/footers and lone page numbers.

    Only the first/last few lines of each page are considered, so repeated
    body text (e.g. many "x.y General" headings) is never touched.
    """
    pages = [body.splitlines() for body in bodies]
    repeated: set[str] = set()
    if len(pages) >= 3:
        seen: dict[str, int] = {}
        for lines in pages:
            for key in {furniture_key(lines[i]) for i in edge_indices(lines)}:
                if key and key != "#" and len(key) <= 160:
                    seen[key] = seen.get(key, 0) + 1
        threshold = max(3, int(len(pages) * 0.3))
        repeated = {k for k, n in seen.items() if n >= threshold}
    # Longest first, so a combined footer ("© A … © B …") is consumed whole.
    parts = sorted(repeated, key=len, reverse=True)

    def is_furniture(line: str) -> bool:
        key = furniture_key(line)
        if not key:
            return False
        if key in repeated or PAGE_NUMBER.match(line.strip()):
            return True
        rest = key
        for part in parts:
            rest = rest.replace(part, " ")
        return rest != key and not re.sub(r"[#\s|-]", "", rest)

    cleaned = []
    for lines in pages:
        drop = {i for i in edge_indices(lines) if is_furniture(lines[i])}
        cleaned.append("\n".join(l for i, l in enumerate(lines) if i not in drop))
    return cleaned


def strip_dot_leader_toc(md: str) -> tuple[str, int]:
    """Remove table-of-contents rows rendered with dot leaders ("1 Scope ....... 1")."""
    lines = md.splitlines()
    toc_rows = {
        i for i, line in enumerate(lines)
        if DOT_LEADER.search(line)
        and (line.strip().startswith("|") or re.search(r"\**[0-9ivxlc]{1,4}\**$", line.strip(), re.I))
    }
    if not toc_rows:
        return md, 0
    out: list[str] = []
    for i, line in enumerate(lines):
        s = line.strip()
        if i in toc_rows or re.fullmatch(r"(?:#+\s*)?\**(?:Page|Página|Pág\.)\**", s):
            continue
        if re.fullmatch(r"\|(?:\s*:?-{3,}:?\s*\|)+", s) and not (out and out[-1].strip().startswith("|")):
            continue  # separator row whose header row was a TOC row
        out.append(line)
    return "\n".join(out), len(toc_rows)


CLAUSE_NUMBER = r"(?:[0-9]{1,2}|[A-Z])(?:\.[0-9]{1,3})+|[0-9]{1,2}"
CLAUSE = re.compile(rf"^({CLAUSE_NUMBER})\.?\s+\S")
CAPTION = re.compile(r"^(?:Figure|Figura|Table|Tabela|Quadro)\s+[A-Z]?[.0-9]+\s*[—–:-]")
ANNEX = re.compile(r"^(?:Annex|Anexo|Appendix|Apêndice)\s+[A-Z]\b")


def heading_text(line: str) -> str:
    return re.sub(r"\*\*|__", "", line.lstrip("#")).strip()


def number_headings(md: str) -> str:
    """Re-level headings from their clause numbers: "1" -> ##, "5.2" -> ###, "A.2.1" -> ####.

    Also rejoins a number split from its title, demotes figure/table captions
    to bold text and puts annex titles at the top clause level.
    """
    lines = md.split("\n")
    # Shift unnumbered headings (Foreword, Bibliography...) by the same amount
    # the top-level clauses move, so they stay in proportion.
    top_levels = [
        len(l) - len(l.lstrip("#"))
        for l in lines
        if l.startswith("#") and re.match(r"^[0-9]{1,2}\s+\S", heading_text(l))
    ]
    offset = 2 - max(set(top_levels), key=top_levels.count) if top_levels else 0
    out: list[str] = []
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        text = heading_text(s)
        is_heading = s.startswith("#")
        if (is_heading or s.startswith("**")) and re.fullmatch(CLAUSE_NUMBER, text) and "." in text:
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and len(heading_text(lines[j])) <= 160:
                lines[j] = f"# {text} {heading_text(lines[j])}"
                i = j
                continue
        if ANNEX.match(text) and len(text) <= 40:
            # "**Annex A** (normative)" followed by the annex title on its own line.
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            nxt = heading_text(lines[j]) if j < len(lines) else ""
            if nxt and lines[j].lstrip().startswith("#") and not (CLAUSE.match(nxt) or ANNEX.match(nxt)):
                out.append(f"## {text} — {heading_text(lines[j])}")
                i = j + 1
                continue
        if is_heading:
            m = CLAUSE.match(text)
            if CAPTION.match(text):
                out.append(f"**{text}**")
            elif ANNEX.match(text):
                out.append(f"## {text}")
            elif m:
                out.append("#" * min(m.group(1).count(".") + 2, 6) + " " + text)
            elif re.match(r"^[a-z]\)\s", text):
                out.append(f"- {text}")  # list item the extractor promoted
            else:
                level = len(s) - len(s.lstrip("#"))
                if level == 1 and not any(o.startswith("# ") for o in out):
                    out.append(lines[i])  # document title
                else:
                    out.append("#" * max(2, min(level + offset, 6)) + " " + text)
        else:
            out.append(lines[i])
        i += 1
    return "\n".join(out)


def build_toc(md: str) -> str:
    entries = []
    for hashes, title in re.findall(r"^(#{2,4}) (.+)$", md, flags=re.M):
        if re.match(r"^\d+\.\d+\.\d+ [a-z]", title):
            continue  # numbered term entries (3.1.1 acquirer), not sections
        slug = re.sub(r"[^\w\s-]", "", title.lower())
        slug = re.sub(r"\s+", "-", slug.strip())
        entries.append("  " * (len(hashes) - 2) + f"- [{title}](#{slug})")
    return "## Contents\n\n" + "\n".join(entries) if entries else ""


def convert(src: Path, dest: Path, args: argparse.Namespace) -> dict:
    doc = pymupdf.open(src)
    if doc.needs_pass and not doc.authenticate(args.password or ""):
        raise PermissionError(f"{src}: encrypted, pass --password")

    pages = parse_pages(args.pages, doc.page_count) if args.pages else None
    kwargs: dict = {
        "pages": pages,
        "header": args.keep_headers,
        "footer": args.keep_headers,
        # Always split per page internally; furniture detection needs it.
        "page_separators": True,
        "show_progress": args.progress,
        "use_ocr": args.ocr != "off",
        "force_ocr": args.ocr == "force",
        "ocr_language": args.lang or default_ocr_language(),
    }
    if args.html_tables:
        kwargs["table_output"] = "html"

    assets = dest.parent / f"{dest.stem}_assets"
    if args.images == "write":
        assets.mkdir(parents=True, exist_ok=True)
        kwargs.update(write_images=True, image_path=str(assets), dpi=args.dpi)
    elif args.images == "embed":
        kwargs.update(embed_images=True, dpi=args.dpi)

    md = pymupdf4llm.to_markdown(doc, **kwargs)

    if args.images == "write":
        # Make image links relative to the .md file and drop the ".pdf" the
        # extractor puts in file names ("doc.pdf-0019-13.png" -> "doc-p0019-13.png").
        md = md.replace(str(assets) + "/", f"{assets.name}/")
        for img in sorted(assets.iterdir()):
            m = re.fullmatch(re.escape(src.name) + r"-(\d+)-(\d+)(\.\w+)", img.name)
            if m:
                new = img.with_name(f"{src.stem}-p{m.group(1)}-{m.group(2)}{m.group(3)}")
                img.rename(new)
                md = md.replace(f"{assets.name}/{img.name}", f"{assets.name}/{new.name}")
        if not any(assets.iterdir()):
            assets.rmdir()

    md = re.sub(r"[ \t]+$", "", md, flags=re.M)
    bodies, numbers = split_pages(md)
    if not args.keep_headers:
        bodies = strip_page_furniture(bodies)
    if args.page_separators:
        md = "".join(
            body + (f"\n\n<!-- page {numbers[k]} -->\n\n" if k < len(numbers) else "")
            for k, body in enumerate(bodies)
        )
    else:
        md = "\n\n".join(bodies)

    toc_rows = 0
    if not args.keep_toc:
        md, toc_rows = strip_dot_leader_toc(md)
    if args.number_headings:
        md = number_headings(md)
    if args.toc:
        # Put the generated TOC where the PDF had its own, or at the top.
        contents = re.compile(
            r"^#+ \**(?:Contents|Table of contents|Sumário|Índice)\**$", re.M | re.I
        )
        found = contents.search(md)
        if found:
            # Only list what follows the PDF's own TOC (skip the cover pages).
            toc = build_toc(md[found.end():])
            md = md[: found.start()] + toc + md[found.end():]
        else:
            md = build_toc(md) + "\n\n" + md

    md = re.sub(r"[ \t]+$", "", md, flags=re.M)
    md = re.sub(r"\n{3,}", "\n\n", md).strip() + "\n"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(md, encoding="utf-8")

    converted = pages if pages is not None else range(doc.page_count)
    no_text = [i + 1 for i in converted if not doc[i].get_text("text").strip()]
    return {
        "pages": len(converted),
        "headings": len(re.findall(r"^#{1,6} ", md, flags=re.M)),
        "tables": len(re.findall(r"^\|(?: *:?-{3,}:? *\|)+ *$", md, flags=re.M))
        + md.count("<table"),
        "no_text_layer": no_text,
        "toc_rows_removed": toc_rows,
        "chars": len(md),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert PDF to Markdown, keeping headings, lists, tables and reading order."
    )
    parser.add_argument("inputs", nargs="+", type=Path, help="PDF files or directories")
    parser.add_argument(
        "-o", "--output", type=Path,
        help="output .md file, or directory (default: next to each PDF)",
    )
    parser.add_argument("-r", "--recursive", action="store_true", help="recurse into directories")
    parser.add_argument("--pages", help='1-based pages, e.g. "1-5,8,20-"')
    parser.add_argument(
        "--images", choices=("none", "write", "embed"), default="none",
        help="write images to <name>_assets/, embed as base64, or skip (default)",
    )
    parser.add_argument("--dpi", type=int, default=150, help="image resolution (default 150)")
    parser.add_argument(
        "--ocr", choices=("auto", "force", "off"), default="auto",
        help="auto: OCR only pages without a text layer (default)",
    )
    parser.add_argument("--lang", help="tesseract languages, e.g. por+eng (default: auto-detect)")
    parser.add_argument("--keep-headers", action="store_true", help="keep running headers/footers and page numbers")
    parser.add_argument(
        "--page-separators", action="store_true",
        help="mark page ends with <!-- page N --> (invisible when rendered)",
    )
    parser.add_argument(
        "--number-headings", action="store_true",
        help="set heading levels from clause numbers (1 -> ##, 1.2 -> ###); for standards, specs, laws",
    )
    parser.add_argument("--toc", action="store_true", help="linked table of contents, in place of the PDF's own or on top")
    parser.add_argument("--keep-toc", action="store_true", help="keep dot-leader tables of contents from the PDF")
    parser.add_argument("--html-tables", action="store_true", help="render tables as HTML (merged cells)")
    parser.add_argument("--password", help="password for encrypted PDFs")
    parser.add_argument("--progress", action="store_true", help="show per-page progress")
    args = parser.parse_args()

    try:
        files = collect_inputs(args.inputs, args.recursive)
    except FileNotFoundError as exc:
        print(f"pdf2md: not found: {exc}", file=sys.stderr)
        return 66
    if not files:
        print("pdf2md: no PDF files found", file=sys.stderr)
        return 66

    many = len(files) > 1
    failures = 0
    for src in files:
        dest = output_path(src, args, many)
        try:
            stats = convert(src, dest, args)
        except Exception as exc:  # keep going through a batch
            failures += 1
            print(f"FAIL {src}: {exc}", file=sys.stderr)
            continue
        line = (
            f"OK   {src} -> {dest} "
            f"({stats['pages']} pages, {stats['headings']} headings, "
            f"{stats['tables']} tables, {stats['chars']} chars)"
        )
        if stats["toc_rows_removed"]:
            line += f" [removed {stats['toc_rows_removed']} dot-leader TOC rows]"
        print(line)
        if stats["no_text_layer"]:
            shown = ",".join(map(str, stats["no_text_layer"][:20]))
            more = "..." if len(stats["no_text_layer"]) > 20 else ""
            hint = "OCR applied" if args.ocr != "off" else "re-run without --ocr off"
            print(f"     pages without text layer: {shown}{more} ({hint}; verify output)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
