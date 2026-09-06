#!/usr/bin/env python3
"""Regenerate PDFs for all fixtures/*.yaml and combine them into one review PDF."""

import io
import pathlib
import shutil
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


def main():
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True)

    review = PdfWriter()

    for yaml_path in sorted(FIXTURES_DIR.glob("*.yaml")):
        data = make_title_pages.load_data(yaml_path)
        pdf_path = OUT_DIR / f"{yaml_path.stem}.pdf"
        make_title_pages.render_pdf(data, pdf_path)
        print(f"wrote {pdf_path}")

        review.append(label_page(yaml_path.name, data.get("page_size", "letter")))
        review.append(PdfReader(str(pdf_path)))

    review_path = OUT_DIR / "_review.pdf"
    with open(review_path, "wb") as f:
        review.write(f)
    print(f"wrote {review_path}")

    subprocess.run(["open", str(review_path)])


if __name__ == "__main__":
    main()
