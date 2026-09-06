#!/usr/bin/env python3
"""Generate a formatted title-page PDF from a YAML description."""

import argparse
import html
import io
import pathlib
import re
import sys

import yaml
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup
from pypdf import PdfReader, PdfWriter
from weasyprint import HTML

REQUIRED_FIELDS = ("title", "composer")
TEMPLATE_DIR = pathlib.Path(__file__).parent
TEMPLATE_NAME = "template.html"
DEFAULT_MULTI_SPEC_OUTPUT = "out.pdf"

COLOR_WARNING = "\033[38;5;208m"
COLOR_OK = "\033[32m"
COLOR_ERROR = "\033[31m"
COLOR_RESET = "\033[0m"


def log(message):
    print(message)


def warn(message):
    print(f"{COLOR_WARNING}warning: {message}{COLOR_RESET}", file=sys.stderr)


def error(message):
    print(f"{COLOR_ERROR}error: {message}{COLOR_RESET}", file=sys.stderr)


def ok(message):
    print(f"{COLOR_OK}{message}{COLOR_RESET}")


def slugify(text):
    slug = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[\s_]+", "-", slug) or "title-page"


def markdown_lite(text):
    escaped = html.escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*(.+?)\*", r"<em>\1</em>", escaped)
    escaped = re.sub(r"_(.+?)_", r"<em>\1</em>", escaped)
    return Markup(escaped)


def render_line(line):
    classes = ["line"]
    if line.startswith("  "):
        classes.append("line-indent")
        line = line.lstrip(" ")

    if "\t" in line:
        left, right = line.split("\t", 1)
        classes.append("line-split")
        return Markup(
            f'<p class="{" ".join(classes)}">'
            f'<span class="line-left">{markdown_lite(left)}</span>'
            f'<span class="line-right">{markdown_lite(right)}</span>'
            "</p>"
        )
    return Markup(f'<p class="{" ".join(classes)}">{markdown_lite(line)}</p>')


def validate_spec(spec, source, label=None):
    spec = spec or {}
    location = str(source) + (f" (entry {label})" if label is not None else "")

    missing = [field for field in REQUIRED_FIELDS if not spec.get(field)]
    if missing:
        sys.exit(f"error: missing required field(s) in {location}: {', '.join(missing)}")

    if "-" in (spec.get("composer_dates") or ""):
        warn("found hyphen in composer_dates, did you mean to use an en-dash (–)?")

    if spec.get("translation") and not spec.get("text"):
        raise NotImplementedError("translation without text is not supported")

    return spec


def load_data(yaml_path):
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return validate_spec(data, yaml_path)


def load_specs(yaml_path):
    with open(yaml_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if isinstance(raw, list):
        if not raw:
            sys.exit(f"error: {yaml_path} contains an empty list")
        return [validate_spec(spec, yaml_path, label=i) for i, spec in enumerate(raw)]

    return [validate_spec(raw, yaml_path)]


def resolve_output_path(data, cli_output):
    outfile_name = data.pop("outfile_name", None)
    if cli_output:
        if outfile_name:
            warn(f"-o overrides outfile_name ({outfile_name!r}) from the YAML")
        return cli_output
    if outfile_name:
        return pathlib.Path(outfile_name)
    return pathlib.Path(f"{slugify(data['title'])}.pdf")


def render_html(data):
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=True)
    env.filters["markdown_lite"] = markdown_lite
    env.filters["render_line"] = render_line
    template = env.get_template(TEMPLATE_NAME)
    return template.render(**data)


def render_pdf_bytes(data):
    return HTML(string=render_html(data), base_url=str(TEMPLATE_DIR)).write_pdf()


def render_pdf(data, output_path):
    with open(output_path, "wb") as f:
        f.write(render_pdf_bytes(data))


def combine_pdfs(pdf_bytes_list, output_path):
    writer = PdfWriter()
    for pdf_bytes in pdf_bytes_list:
        writer.append(PdfReader(io.BytesIO(pdf_bytes)))
    with open(output_path, "wb") as f:
        writer.write(f)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("yaml_file", type=pathlib.Path, help="YAML file describing one or more title pages")
    parser.add_argument("-o", "--output", type=pathlib.Path, help="output PDF path (default: <title>.pdf)")
    parser.add_argument(
        "--multifile",
        action="store_true",
        help="for a YAML list of specs, write one PDF per entry instead of combining into one",
    )
    args = parser.parse_args()

    if args.multifile and args.output:
        parser.error("-o cannot be used with --multifile")

    specs = load_specs(args.yaml_file)

    if len(specs) == 1:
        output_path = resolve_output_path(specs[0], args.output)
        render_pdf(specs[0], output_path)
        ok(f"wrote {output_path}")
    elif args.multifile:
        for spec in specs:
            output_path = resolve_output_path(spec, None)
            render_pdf(spec, output_path)
            ok(f"wrote {output_path}")
    else:
        output_path = args.output or pathlib.Path(DEFAULT_MULTI_SPEC_OUTPUT)
        combine_pdfs([render_pdf_bytes(spec) for spec in specs], output_path)
        ok(f"wrote {output_path}")


if __name__ == "__main__":
    main()
