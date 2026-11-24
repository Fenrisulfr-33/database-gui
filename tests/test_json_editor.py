"""Tests for the JSON editor card (needs a display, skipped without one).

Author: Archer
"""

import pytest

tk = pytest.importorskip("tkinter")

from db_gui.gui.widgets import json_editor  # noqa: E402


@pytest.fixture
def root():
    try:
        window = tk.Tk()
    except tk.TclError:
        pytest.skip("No display available for Tk")
    window.withdraw()
    yield window
    window.destroy()


@pytest.fixture
def make_editor(root):
    """Factory: (editor, list of every is_valid it reported)."""
    def factory():
        reports: list[bool] = []
        editor = json_editor.JsonEditor(root, reports.append)
        return editor, reports

    return factory


def gutter_text(editor) -> str:
    return editor.gutter.get("1.0", "end-1c")


def test_json_editor_starts_with_template_and_is_valid(make_editor) -> None:
    editor, reports = make_editor()

    assert editor.get_text() == json_editor.JSON_TEMPLATE
    assert editor.error == ""
    assert reports[-1] is True
    assert "Valid document" in editor.validity.cget("text")
    assert gutter_text(editor) == "1\n2\n3"


def test_set_text_reports_invalid_json(make_editor) -> None:
    editor, reports = make_editor()

    editor.set_text('{"name": ')

    assert reports[-1] is False
    assert "Invalid JSON" in editor.validity.cget("text")


def test_set_text_rejects_non_object(make_editor) -> None:
    editor, _reports = make_editor()

    editor.set_text("[1, 2]")

    assert "must be a JSON object" in editor.error


def test_get_document_reads_extended_json(make_editor) -> None:
    editor, _reports = make_editor()
    editor.set_text('{"_id": {"$oid": "671d8e2f4a9b0c1234567890"}, "n": 1}')

    document = editor.get_document()

    assert str(document["_id"]) == "671d8e2f4a9b0c1234567890"
    assert document["n"] == 1


def test_format_json_reindents_and_keeps_extended_json(make_editor) -> None:
    editor, _reports = make_editor()
    editor.set_text('{"_id": {"$oid": "abc"}, "tags": ["a"]}')

    editor.format_json()

    assert editor.get_text() == (
        '{\n  "_id": {\n    "$oid": "abc"\n  },\n  "tags": [\n    "a"\n  ]\n}')
    assert gutter_text(editor).splitlines()[-1] == "8"


def test_format_json_leaves_invalid_text_alone(make_editor) -> None:
    editor, _reports = make_editor()
    editor.set_text("{bad")

    editor.format_json()

    assert editor.get_text() == "{bad"


def test_highlight_tags_keys_strings_and_literals(make_editor) -> None:
    editor, _reports = make_editor()

    editor.set_text('{"a": "b", "c": true, "d": 12}')

    def tagged(tag: str) -> list[str]:
        ranges = editor.text.tag_ranges(tag)
        return [editor.text.get(start, end)
                for start, end in zip(ranges[::2], ranges[1::2])]

    assert tagged("key") == ['"a"', '"c"', '"d"']
    assert tagged("string") == ['"b"']
    assert tagged("literal") == ["true", "12"]


def test_cursor_position_and_size_in_footer(make_editor) -> None:
    editor, _reports = make_editor()
    editor.set_text('{"a": 1}')
    editor.text.mark_set("insert", "1.3")

    editor._update_cursor()

    assert editor.position.cget("text") == "Ln 1, Col 4    UTF-8    8 B"


def test_tab_inserts_two_spaces(make_editor) -> None:
    editor, _reports = make_editor()
    editor.set_text("")

    assert editor._insert_indent() == "break"
    assert editor.get_text() == "  "
