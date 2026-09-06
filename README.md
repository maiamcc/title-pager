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
[x] Ability to specify name of output file in YAML
	* use key `outfile_name` in YAML to allow for specifying the name of the generated file (same behavior is `-o` when invoking)
	* a passed `-o` flag overrides the value from the yaml (but displays a warning)
	* behavior without `-o` and without `outfile_name` is the same--derive output name from title
[x] Ability to generate multiple title pages from a single yaml file
	* a yaml file may contain a LIST of title page specs eg:
	```
	- title: Virga Jesse
	  composer: Anton Bruckner
	- title: Call Me Maybe
	  composer: C.R. Jepsen
	```
	* in the above case, two different title pages should be generated
	* by default, output to one pdf per entry (in this case, the `-o` file dictates the name of the single output file)
	* if `--multifile` flag passed, output each item to its own pdf file (`-o` is invalid with `--multifile` and a file contain multiple specs and should result in an error)
	* if a yaml file has a single item in it, keep current behavior
[x] centered single-text
	* for an item with only `text` and no `translation`, the  box containing that text should be horizontally centered in the page (the attribution, if any, remains right-justified within the box)
[x] line continuations
	* line continuations in a text or translation should have a hanging indent on all lines besides the first
[x] markdown support
	* in text/translation, support simple markdown: `**` for bold, `*` or `_` for italics.
	* you should be able to cover this in unit tests--assert that the resulting html has `<strong>` or `<em>` tags as appropriate
* sizing and formatting
	- size titles etc
	- what gets italic and what doesn't
	- box sizing and alignment
	- positioning esp of dedication, etc. (should I just remove dedication?)
* markdown support
* keep text/translation lines correlated, pretty line spillover
* keep text/translation boxes same size
* add marker for "fixtures identical, no need for re-review"
* fixtures in one yaml
