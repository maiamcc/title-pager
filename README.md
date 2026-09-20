# title-pager

Generate a formatted choral title-page PDF from a YAML description.

NB: this code written by Claude, all mistakes are because Claude is a stupid robot.

## Setup

```bash
python3 -m venv ~/.virtualenvs/title-pager
source ~/.virtualenvs/title-pager/bin/activate
pip install -r requirements-dev.txt
```

(`requirements-dev.txt` pulls in `requirements.txt` plus test tooling.)

## Running

```bash
source ~/.virtualenvs/title-pager/bin/activate
./make_title_pages.py your_piece.yaml -o "Your Piece.pdf"
```

`title` and `composer` are required; everything else (`composer_dates`,
`subtitle`, `dedication`, `text`, `page_size`) is optional. See
[example.yaml](example.yaml) for the full field shape: `text` holds
`stanzas` (each a `lines` list, optionally paired with a `translation_lines`
list of the same length) plus an optional `attribution` and `box` (default
true, applies to both columns). A translation column only appears when at
least one stanza has `translation_lines`.

Omit `-o` and the output filename is derived from the title.

`composer_dates` is meant to hold an en dash (`–`), e.g. `"1872–1958"`; a
plain hyphen there prints a warning as a likely typo.

## Text formatting

These conventions apply within string values (`title`, `subtitle`,
`dedication`, and stanza `lines`/`translation_lines`, except where noted).
Several rely on an escape sequence (`\n`, `\t`) that YAML only interprets
inside a **double-quoted** string — a plain or single-quoted scalar keeps
those as literal backslash-n/backslash-t, not the special character.

* **`**bold**`, `*italic*` / `_italic_`** — markdown-lite emphasis.
  Supported in `title`, `subtitle`, `dedication`, and stanza
  `lines`/`translation_lines`. Not supported in `attribution`.
* **`\n`** — forces a line break. Only meaningful in `title` and
  `subtitle` (stanza lines are already a YAML list, one line each, so they
  don't need it). Example: `title: "Now Is the Month\nof Maying"`.
* **`\t`** — splits a single stanza line into a left-aligned and a
  right-aligned span (e.g. original-language text paired with a bracketed
  gloss on the same line). Example:
  `"Virga Jesse floruit:\t[The rod of Jesse hath blossomed:]"`.
* **Leading two spaces** (`"  like this"`) — indents that line (a hanging
  indent relative to the rest of the stanza), for things like a refrain or
  a sub-line of the line above it. A single leading space is not enough to
  trigger it.

The title and the two-column text/translation boxes also auto-flex to
avoid unnecessary line wraps: if a title or a box's content would wrap at
the default page margins but a small margin squeeze would let it fit on
one line, the margins narrow just enough to do that (falling back to the
default margins, wrap and all, if even the minimum margin wouldn't help).
This is automatic and doesn't need any special syntax — see the
`title-margin-squeeze` and width-flex cases in
[fixtures/fixtures.yaml](fixtures/fixtures.yaml) for examples.

## Testing

Unit tests (fast, no PDF rendering):

```bash
pytest -q
```

Visual spot-check — regenerates every case in [fixtures/fixtures.yaml](fixtures/fixtures.yaml)
(one YAML list, each entry a full spec) and opens a combined review PDF
(each case preceded by a label page) in Preview:

```bash
./regen_fixtures.py
```

Add new brittle/common cases as entries in that list rather than writing
one-off assertions — this keeps the suite easy to extend without rewriting
tests for every small formatting change. Keep each case earning its place:
it should exercise something no other case does (see the comments at the
top of the file for the current set's reasoning).

## TODO
* sizing and formatting
	- what gets italic and what doesn't
	- box sizing and alignment
	- positioning esp of dedication, etc. (should I just remove dedication?)
* attriubtion for trans. in addition to text
	* keep text/translation boxes same size
* text/translation labels
