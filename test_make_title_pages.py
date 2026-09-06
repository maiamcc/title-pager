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
