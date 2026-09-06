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

# Must stay in sync with the corresponding values in template.html's CSS.
BOX_FONT_SIZE_PT = 11.5
BOX_PADDING_IN = 0.25
DEFAULT_COLUMN_GAP_IN = 0.6
DEFAULT_PAGE_MARGIN_SIDE_IN = 1.0
INDENT_EM = 3
SPLIT_GAP_EM = 1

# How far the correlated boxes are allowed to squeeze the gap between them
# and encroach into the normal page margin -- but only when doing so would
# actually eliminate a line break that the default spacing would otherwise
# force. When default spacing already fits, or squeezing all the way to
# these floors still wouldn't be enough, the defaults above are used as-is.
MIN_COLUMN_GAP_IN = 0.3
MIN_PAGE_MARGIN_SIDE_IN = 0.55

PAGE_WIDTHS_IN = {
    "letter": 8.5,
    "legal": 8.5,
    "tabloid": 11,
    "ledger": 17,
    "a3": 297 / 25.4,
    "a4": 210 / 25.4,
    "a5": 148 / 25.4,
}

FONT_CANDIDATES = (
    pathlib.Path.home() / "Library" / "Fonts" / "Minion Pro Regular.ttf",
    pathlib.Path("/Library/Fonts/Minion Pro Regular.ttf"),
)

AVERAGE_CHAR_WIDTH_EM = 0.5
MEASUREMENT_SAFETY_MARGIN = 1.03

_font_metrics_cache = {}


def _load_font_metrics():
    if "metrics" in _font_metrics_cache:
        return _font_metrics_cache["metrics"]

    metrics = None
    for path in FONT_CANDIDATES:
        if path.exists():
            try:
                from fontTools.ttLib import TTFont

                font = TTFont(str(path))
                metrics = (font.getBestCmap(), font["hmtx"], font["head"].unitsPerEm)
            except Exception:
                metrics = None
            break

    _font_metrics_cache["metrics"] = metrics
    return metrics


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


def measure_text_width_in(text, font_size_pt=BOX_FONT_SIZE_PT):
    if not text:
        return 0.0

    metrics = _load_font_metrics()
    if metrics is None:
        raw_in = len(text) * AVERAGE_CHAR_WIDTH_EM * font_size_pt / 72
    else:
        cmap, hmtx, units_per_em = metrics
        total_units = 0
        for ch in text:
            glyph_name = cmap.get(ord(ch))
            try:
                total_units += hmtx[glyph_name][0] if glyph_name else units_per_em * AVERAGE_CHAR_WIDTH_EM
            except KeyError:
                total_units += units_per_em * AVERAGE_CHAR_WIDTH_EM
        raw_in = total_units / units_per_em * font_size_pt / 72

    # Glyph advance widths are summed without kerning/shaping, which
    # WeasyPrint's real (Pango-based) text layout does apply -- a small
    # safety margin keeps borderline lines from wrapping by a hair after
    # sizing the box to this estimate.
    return raw_in * MEASUREMENT_SAFETY_MARGIN


def strip_markdown_for_measurement(text):
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)
    return text


def measure_line_width_in(line):
    indented = line.startswith("  ")
    if indented:
        line = line.lstrip(" ")

    if "\t" in line:
        left, right = line.split("\t", 1)
        width = measure_text_width_in(strip_markdown_for_measurement(left)) + measure_text_width_in(
            strip_markdown_for_measurement(right)
        )
        width += SPLIT_GAP_EM * BOX_FONT_SIZE_PT / 72
    else:
        width = measure_text_width_in(strip_markdown_for_measurement(line))

    if indented:
        width += INDENT_EM * BOX_FONT_SIZE_PT / 72

    return width


def compute_ideal_content_width_in(text):
    widths = [0.0]
    for stanza in text.get("stanzas") or []:
        for line in stanza.get("lines") or []:
            widths.append(measure_line_width_in(line))
        for line in stanza.get("translation_lines") or []:
            widths.append(measure_line_width_in(line))

    if text.get("attribution"):
        widths.append(measure_text_width_in(f'— {text["attribution"]}'))

    return max(widths)


def compute_correlated_layout(text, page_size):
    """Compute the box width, column gap, and row width for the two
    correlated (text + translation) boxes.

    Boxes normally flex up to a cap based on the default margin and gap.
    If content would still wrap even at that cap, the margin and gap are
    squeezed together (in proportion to their own squeezable range) just
    far enough to fit -- but only that far, and only when it actually
    eliminates the wrap. If even the minimum margin/gap wouldn't fit the
    content, the defaults are used as-is (a wrap that can't be avoided
    isn't worth cramping every page for).
    """
    ideal_box_in = compute_ideal_content_width_in(text) + 2 * BOX_PADDING_IN
    page_width_in = PAGE_WIDTHS_IN.get((page_size or "letter").lower(), PAGE_WIDTHS_IN["letter"])

    default_cap_in = (page_width_in - 2 * DEFAULT_PAGE_MARGIN_SIDE_IN - DEFAULT_COLUMN_GAP_IN) / 2

    if ideal_box_in <= default_cap_in:
        gap_in = DEFAULT_COLUMN_GAP_IN
        box_width_in = ideal_box_in
    else:
        # Total extra width buyable by squeezing margin (both sides) and
        # gap down to their floors together.
        squeeze_range_in = (
            2 * (DEFAULT_PAGE_MARGIN_SIDE_IN - MIN_PAGE_MARGIN_SIDE_IN)
            + (DEFAULT_COLUMN_GAP_IN - MIN_COLUMN_GAP_IN)
        ) / 2
        max_cap_in = default_cap_in + squeeze_range_in

        if ideal_box_in > max_cap_in:
            gap_in = DEFAULT_COLUMN_GAP_IN
            box_width_in = default_cap_in
        else:
            # Squeeze margin and gap together, proportionally to their own
            # squeezable range, just far enough to fit the content exactly.
            t = (ideal_box_in - default_cap_in) / squeeze_range_in
            gap_in = DEFAULT_COLUMN_GAP_IN - t * (DEFAULT_COLUMN_GAP_IN - MIN_COLUMN_GAP_IN)
            box_width_in = ideal_box_in

    box_width_in = round(box_width_in, 3)
    gap_in = round(gap_in, 3)
    row_width_in = round(2 * box_width_in + gap_in, 3)

    # WeasyPrint's grid layout doesn't resolve margin:auto correctly when
    # the grid is wider than its containing block (confirmed by direct
    # testing -- it collapses to flush-left instead of centering), so the
    # left offset needed to keep the row centered on the *default*
    # printable area (even when squeezed wider than it) is computed here
    # and applied as an explicit margin-left instead of auto.
    printable_width_in = page_width_in - 2 * DEFAULT_PAGE_MARGIN_SIDE_IN
    row_margin_left_in = round((printable_width_in - row_width_in) / 2, 3)

    return {
        "box_width_in": box_width_in,
        "column_gap_in": gap_in,
        "row_width_in": row_width_in,
        "row_margin_left_in": row_margin_left_in,
    }


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

    missing = [field for field in REQUIRED_FIELDS if not spec.get(field)]
    if missing:
        location = str(source) + (f" (entry {label})" if label is not None else "")
        sys.exit(f"error: missing required field(s) in {location}: {', '.join(missing)}")

    if "-" in (spec.get("composer_dates") or ""):
        warn("found hyphen in composer_dates, did you mean to use an en-dash (–)?")

    for i, stanza in enumerate(((spec.get("text") or {}).get("stanzas")) or []):
        translation_lines = stanza.get("translation_lines")
        if translation_lines is not None:
            n_lines = len(stanza.get("lines") or [])
            n_translation = len(translation_lines)
            if n_lines != n_translation:
                warn(
                    f"stanza {i} has {n_lines} lines but {n_translation} translation_lines"
                )

    return spec


def build_translation_block(text):
    if not text:
        return None
    stanzas = text.get("stanzas") or []
    if not any("translation_lines" in stanza for stanza in stanzas):
        return None
    return {
        "stanzas": [{"lines": stanza.get("translation_lines") or []} for stanza in stanzas],
        "box": text.get("box", True),
    }


def build_correlated_rows(text):
    rows = []
    for stanza in text.get("stanzas") or []:
        lines = stanza.get("lines") or []
        translation_lines = stanza.get("translation_lines")
        row_count = max(len(lines), len(translation_lines or []))
        for i in range(row_count):
            rows.append(
                {
                    "left": render_line(lines[i]) if i < len(lines) else None,
                    "right": (
                        render_line(translation_lines[i])
                        if translation_lines is not None and i < len(translation_lines)
                        else None
                    ),
                    "stanza_start": i == 0,
                }
            )

    if text.get("attribution"):
        rows.append(
            {
                "left": Markup(f'<p class="attribution">— {html.escape(text["attribution"])}</p>'),
                "right": None,
                "stanza_start": False,
            }
        )

    for idx, row in enumerate(rows, start=1):
        row["row_number"] = idx

    left_numbers = [row["row_number"] for row in rows if row["left"] is not None]
    right_numbers = [row["row_number"] for row in rows if row["right"] is not None]

    first_candidates = [n[0] for n in (left_numbers, right_numbers) if n]
    last_candidates = [n[-1] for n in (left_numbers, right_numbers) if n]

    return {
        "rows": rows,
        "left_first_row": left_numbers[0] if left_numbers else None,
        "left_last_row": left_numbers[-1] if left_numbers else None,
        "right_first_row": right_numbers[0] if right_numbers else None,
        "right_last_row": right_numbers[-1] if right_numbers else None,
        # Both boxes end at the same row (the taller of the two), so a
        # trailing element on one side (e.g. attribution) leaves matching
        # blank space in the other rather than the boxes ending at
        # different heights.
        "frame_first_row": min(first_candidates) if first_candidates else None,
        "frame_last_row": max(last_candidates) if last_candidates else None,
        "box": text.get("box", True),
    }


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
    text = data.get("text")
    translation = build_translation_block(text)
    context = {**data, "translation": translation}
    if text and translation:
        context["correlated"] = build_correlated_rows(text)
        context.update(compute_correlated_layout(text, data.get("page_size")))
    return template.render(**context)


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
