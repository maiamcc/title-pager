#!/usr/bin/env python3
"""Regenerate PDFs for every case in fixtures/fixtures.yaml, combine them
into one review PDF, and open only the individual case PDFs that changed
since the last run."""

import html
import io
import pathlib
import subprocess

from pypdf import PdfReader, PdfWriter
from weasyprint import HTML

import make_title_pages

FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"
FIXTURES_FILE = FIXTURES_DIR / "fixtures.yaml"
OUT_DIR = FIXTURES_DIR / "out"
MANY_CHANGES_THRESHOLD = 4


def label_page(name, metadata, page_size):
    metadata_html = (
        f'<p style="font-size:14pt;color:#444;max-width:80%;margin-top:0.5em;">{html.escape(metadata)}</p>'
        if metadata
        else ""
    )
    page_html = f"""
    <html><head><style>@page {{ size: {page_size}; margin: 0; }}</style></head>
    <body style="margin:0;height:100vh;display:flex;flex-direction:column;
    align-items:center;justify-content:center;text-align:center;font-family:sans-serif;">
    <p style="font-size:24pt;margin:0;">{html.escape(name)}</p>
    {metadata_html}
    </body></html>
    """
    return PdfReader(io.BytesIO(HTML(string=page_html).write_pdf()))


def build_case_pdf_bytes(spec):
    writer = PdfWriter()
    writer.append(label_page(spec["title"], spec.get("metadata"), spec.get("page_size", "letter")))
    writer.append(PdfReader(io.BytesIO(make_title_pages.render_pdf_bytes(spec))))
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    specs = make_title_pages.load_specs(FIXTURES_FILE)

    review = PdfWriter()
    changed_paths = []

    for spec in specs:
        pdf_path = OUT_DIR / f"{make_title_pages.slugify(spec['title'])}.pdf"

        new_bytes = build_case_pdf_bytes(spec)
        old_bytes = pdf_path.read_bytes() if pdf_path.exists() else None
        changed = new_bytes != old_bytes

        pdf_path.write_bytes(new_bytes)
        print(f"wrote {pdf_path} ({'changed' if changed else 'unchanged'})")

        if changed:
            changed_paths.append(pdf_path)

        review.append(PdfReader(io.BytesIO(new_bytes)))

    review_path = OUT_DIR / "_review.pdf"
    with open(review_path, "wb") as f:
        review.write(f)
    print(f"wrote {review_path}")

    if not changed_paths:
        print("no fixtures changed since last run; nothing to review")
    elif len(changed_paths) >= MANY_CHANGES_THRESHOLD:
        print(f"{len(changed_paths)} fixtures changed; opening {review_path} instead")
        subprocess.run(["open", str(review_path)])
    else:
        print(f"opening {len(changed_paths)} changed fixture(s) for review")
        subprocess.run(["open", *[str(p) for p in changed_paths]])


if __name__ == "__main__":
    main()
