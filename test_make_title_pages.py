import pathlib

import pytest

import make_title_pages


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Virga Jesse", "virga-jesse"),
        ("Ave Maria: gratia plena", "ave-maria-gratia-plena"),
        ("  Locus   Iste  ", "locus-iste"),
        ("¡Hola!", "hola"),
        ("", "title-page"),
        ("!!!", "title-page"),
    ],
)
def test_slugify(text, expected):
    assert make_title_pages.slugify(text) == expected


def write_yaml(tmp_path, contents):
    path = tmp_path / "input.yaml"
    path.write_text(contents, encoding="utf-8")
    return path


def test_load_data_valid_minimal(tmp_path):
    path = write_yaml(tmp_path, "title: Foo\ncomposer: Bar\n")
    data = make_title_pages.load_data(path)
    assert data == {"title": "Foo", "composer": "Bar"}


def test_load_data_missing_title(tmp_path):
    path = write_yaml(tmp_path, "composer: Bar\n")
    with pytest.raises(SystemExit, match="title"):
        make_title_pages.load_data(path)


def test_load_data_missing_composer(tmp_path):
    path = write_yaml(tmp_path, "title: Foo\n")
    with pytest.raises(SystemExit, match="composer"):
        make_title_pages.load_data(path)


def test_load_data_missing_both(tmp_path):
    path = write_yaml(tmp_path, "subtitle: Foo\n")
    with pytest.raises(SystemExit, match="title, composer"):
        make_title_pages.load_data(path)


def test_load_data_empty_file(tmp_path):
    path = write_yaml(tmp_path, "")
    with pytest.raises(SystemExit, match="title, composer"):
        make_title_pages.load_data(path)


def test_load_data_translation_without_text_not_implemented(tmp_path):
    path = write_yaml(
        tmp_path,
        """
        title: Foo
        composer: Bar
        translation:
          stanzas:
            - lines:
                - Hello
        """,
    )
    with pytest.raises(NotImplementedError):
        make_title_pages.load_data(path)


def test_load_data_text_without_translation_is_fine(tmp_path):
    path = write_yaml(
        tmp_path,
        """
        title: Foo
        composer: Bar
        text:
          stanzas:
            - lines:
                - Hello
        """,
    )
    data = make_title_pages.load_data(path)
    assert data["text"]["stanzas"][0]["lines"] == ["Hello"]


def test_resolve_output_path_defaults_to_slugified_title():
    data = {"title": "Virga Jesse", "composer": "Bar"}
    path = make_title_pages.resolve_output_path(data, None)
    assert path == pathlib.Path("virga-jesse.pdf")


def test_resolve_output_path_uses_outfile_name(tmp_path):
    data = {"title": "Foo", "composer": "Bar", "outfile_name": "Custom Name.pdf"}
    path = make_title_pages.resolve_output_path(data, None)
    assert path == pathlib.Path("Custom Name.pdf")
    assert "outfile_name" not in data


def test_resolve_output_path_cli_overrides_outfile_name(capsys):
    data = {"title": "Foo", "composer": "Bar", "outfile_name": "Custom Name.pdf"}
    path = make_title_pages.resolve_output_path(data, pathlib.Path("cli.pdf"))
    assert path == pathlib.Path("cli.pdf")
    assert "outfile_name" not in data
    assert "warning" in capsys.readouterr().err.lower()


def test_resolve_output_path_cli_without_outfile_name_no_warning(capsys):
    data = {"title": "Foo", "composer": "Bar"}
    path = make_title_pages.resolve_output_path(data, pathlib.Path("cli.pdf"))
    assert path == pathlib.Path("cli.pdf")
    assert capsys.readouterr().err == ""


def test_load_specs_bare_dict_returns_single_item_list(tmp_path):
    path = write_yaml(tmp_path, "title: Foo\ncomposer: Bar\n")
    specs = make_title_pages.load_specs(path)
    assert specs == [{"title": "Foo", "composer": "Bar"}]


def test_load_specs_one_item_list_returns_single_item_list(tmp_path):
    path = write_yaml(tmp_path, "- title: Foo\n  composer: Bar\n")
    specs = make_title_pages.load_specs(path)
    assert specs == [{"title": "Foo", "composer": "Bar"}]


def test_load_specs_multi_item_list(tmp_path):
    path = write_yaml(
        tmp_path,
        """
        - title: Virga Jesse
          composer: Anton Bruckner
        - title: Call Me Maybe
          composer: C.R. Jepsen
        """,
    )
    specs = make_title_pages.load_specs(path)
    assert [s["title"] for s in specs] == ["Virga Jesse", "Call Me Maybe"]


def test_load_specs_empty_list_errors(tmp_path):
    path = write_yaml(tmp_path, "[]\n")
    with pytest.raises(SystemExit, match="empty list"):
        make_title_pages.load_specs(path)


def test_load_specs_missing_field_in_one_entry_names_it(tmp_path):
    path = write_yaml(
        tmp_path,
        """
        - title: Virga Jesse
          composer: Anton Bruckner
        - title: Call Me Maybe
        """,
    )
    with pytest.raises(SystemExit, match=r"entry 1.*composer"):
        make_title_pages.load_specs(path)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("**bold**", "<strong>bold</strong>"),
        ("*italic*", "<em>italic</em>"),
        ("_italic_", "<em>italic</em>"),
        ("**bold** and *italic*", "<strong>bold</strong> and <em>italic</em>"),
        ("plain text", "plain text"),
        ("Ben & Jerry's <3", "Ben &amp; Jerry&#x27;s &lt;3"),
    ],
)
def test_markdown_lite(text, expected):
    assert make_title_pages.markdown_lite(text) == expected


def test_render_line_without_tab():
    assert make_title_pages.render_line("plain text") == '<p class="line">plain text</p>'


def test_render_line_with_tab_splits_into_left_and_right_spans():
    result = make_title_pages.render_line("left part\tright part")
    assert result == (
        '<p class="line line-split">'
        '<span class="line-left">left part</span>'
        '<span class="line-right">right part</span>'
        "</p>"
    )


def test_render_line_with_leading_two_spaces_is_indented():
    result = make_title_pages.render_line("  indented line")
    assert result == '<p class="line line-indent">indented line</p>'


def test_render_line_single_leading_space_is_not_indented():
    result = make_title_pages.render_line(" one space")
    assert "line-indent" not in result


def test_render_line_indent_and_tab_split_combine():
    result = make_title_pages.render_line("  left\tright")
    assert result == (
        '<p class="line line-indent line-split">'
        '<span class="line-left">left</span>'
        '<span class="line-right">right</span>'
        "</p>"
    )


def test_render_line_applies_markdown_to_both_sides_of_tab():
    result = make_title_pages.render_line("*left*\t**right**")
    assert "<span class=\"line-left\"><em>left</em></span>" in result
    assert "<span class=\"line-right\"><strong>right</strong></span>" in result


def test_render_line_only_splits_on_first_tab():
    result = make_title_pages.render_line("a\tb\tc")
    assert '<span class="line-right">b\tc</span>' in result


def test_render_html_has_strong_and_em_tags(tmp_path):
    path = write_yaml(
        tmp_path,
        """
        title: Foo
        composer: Bar
        text:
          stanzas:
            - lines:
                - "**bold** and *italic* and _also italic_"
        """,
    )
    data = make_title_pages.load_data(path)
    html = make_title_pages.render_html(data)
    assert "<strong>bold</strong>" in html
    assert "<em>italic</em>" in html
    assert "<em>also italic</em>" in html


def test_render_html_escapes_other_fields(tmp_path):
    path = write_yaml(tmp_path, 'title: "Foo & Bar"\ncomposer: Baz\n')
    data = make_title_pages.load_data(path)
    html = make_title_pages.render_html(data)
    assert "Foo &amp; Bar" in html


def test_combine_pdfs_concatenates_pages(tmp_path):
    data_a = {"title": "First Piece", "composer": "A"}
    data_b = {"title": "Second Piece", "composer": "B"}
    pdf_bytes = [
        make_title_pages.render_pdf_bytes(data_a),
        make_title_pages.render_pdf_bytes(data_b),
    ]
    output_path = tmp_path / "combined.pdf"
    make_title_pages.combine_pdfs(pdf_bytes, output_path)

    from pypdf import PdfReader

    reader = PdfReader(str(output_path))
    assert len(reader.pages) == 2
    assert "First Piece" in reader.pages[0].extract_text()
    assert "Second Piece" in reader.pages[1].extract_text()
