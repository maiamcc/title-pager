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

## Testing

Unit tests (fast, no PDF rendering):

```bash
pytest -q
```

Visual spot-check — regenerates every fixture in `fixtures/*.yaml` and opens
a combined review PDF (each case preceded by a label page) in Preview:

```bash
./regen_fixtures.py
```

Add new brittle/common cases as `fixtures/<name>.yaml` rather than writing
one-off assertions — this keeps the suite easy to extend without rewriting
tests for every small formatting change.

## TODO
* sizing and formatting
	- what gets italic and what doesn't
	- box sizing and alignment
	- positioning esp of dedication, etc. (should I just remove dedication?)
* attriubtion for trans. in addition to text
	* keep text/translation boxes same size
* flexible width of text boxes to avoid as many line breaks as possible??
* fixtures in one yaml / remove useless ones
* text/translation labels
