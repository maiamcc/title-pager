#!/usr/bin/env python3
"""Regenerate PDFs for all fixtures/*.yaml, combine them into one review PDF,
and open only the individual fixture PDFs that changed since the last run."""

import io
import pathlib
import subprocess

from pypdf import PdfReader, PdfWriter
from weasyprint import HTML

import make_title_pages

FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"
OUT_DIR = FIXTURES_DIR / "out"


def label_page(name, page_size):
    html = f"""
    <html><head><style>@page {{ size: {page_size}; margin: 0; }}</style></head>
    <body style="margin:0;height:100vh;display:flex;
    align-items:center;justify-content:center;font-family:sans-serif;font-size:24pt;">
    {name}
    </body></html>
    """
    return PdfReader(io.BytesIO(HTML(string=html).write_pdf()))


def build_fixture_pdf_bytes(specs):
    if len(specs) == 1:
        return make_title_pages.render_pdf_bytes(specs[0])

    writer = PdfWriter()
    for spec in specs:
        writer.append(PdfReader(io.BytesIO(make_title_pages.render_pdf_bytes(spec))))
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    review = PdfWriter()
    changed_paths = []

    for yaml_path in sorted(FIXTURES_DIR.glob("*.yaml")):
        specs = make_title_pages.load_specs(yaml_path)
        pdf_path = OUT_DIR / f"{yaml_path.stem}.pdf"

        new_bytes = build_fixture_pdf_bytes(specs)
        old_bytes = pdf_path.read_bytes() if pdf_path.exists() else None
        changed = new_bytes != old_bytes

        pdf_path.write_bytes(new_bytes)
        print(f"wrote {pdf_path} ({'changed' if changed else 'unchanged'})")

        if changed:
            changed_paths.append(pdf_path)

        review.append(label_page(yaml_path.name, specs[0].get("page_size", "letter")))
        review.append(PdfReader(io.BytesIO(new_bytes)))

    review_path = OUT_DIR / "_review.pdf"
    with open(review_path, "wb") as f:
        review.write(f)
    print(f"wrote {review_path}")

    if changed_paths:
        print(f"opening {len(changed_paths)} changed fixture(s) for review")
        subprocess.run(["open", *[str(p) for p in changed_paths]])
    else:
        print("no fixtures changed since last run; nothing to review")


if __name__ == "__main__":
    main()
