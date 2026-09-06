# title-pager

Generate a formatted choral title-page PDF from a YAML description.

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
`subtitle`, `dedication`, `text`, `translation`, `page_size`) is optional.
See [example.yaml](example.yaml) for the full field shape, including the
`stanzas`/`lines`/`attribution` structure for `text` and `translation`.

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

* centered single-text
* sizing and formatting
* markdown support
* keep text/translation lines correlated, pretty line spillover
* keep text/translation boxes same size
