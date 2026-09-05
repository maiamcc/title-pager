#!/usr/bin/env python3
"""Generate a formatted title-page PDF from a YAML description."""

import argparse
import pathlib
import re
import sys

import yaml
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

REQUIRED_FIELDS = ("title", "composer")
TEMPLATE_DIR = pathlib.Path(__file__).parent
TEMPLATE_NAME = "template.html"


def slugify(text):
    slug = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[\s_]+", "-", slug) or "title-page"


def load_data(yaml_path):
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    missing = [field for field in REQUIRED_FIELDS if not data.get(field)]
    if missing:
        sys.exit(f"error: missing required field(s) in {yaml_path}: {', '.join(missing)}")

    return data


def render_pdf(data, output_path):
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template(TEMPLATE_NAME)
    html = template.render(**data)
    HTML(string=html, base_url=str(TEMPLATE_DIR)).write_pdf(output_path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("yaml_file", type=pathlib.Path, help="YAML file describing the title page")
    parser.add_argument("-o", "--output", type=pathlib.Path, help="output PDF path (default: <title>.pdf)")
    args = parser.parse_args()

    data = load_data(args.yaml_file)
    output_path = args.output or pathlib.Path(f"{slugify(data['title'])}.pdf")

    render_pdf(data, output_path)
    print(f"wrote {output_path}")


if __name__ == "__main__":
    main()
