"""Tests for the Documents page (needs a display, skipped without one).

Author: Archer (rewritten for the restyled page on the cluster frame)
"""

import pytest

tk = pytest.importorskip("tkinter")

from conftest import make_shell, wait_for_load  # noqa: E402
from db_gui.db.connection import ImportResult  # noqa: E402
from db_gui.gui.views import document_view  # noqa: E402
from db_gui.gui.views.document_view import (DocumentPage,  # noqa: E402
                                            DocumentView)
from db_gui.gui.widgets.schema_tab import SchemaActions  # noqa: E402


@pytest.fixture
def root():
    try:
        window = tk.Tk()
    except tk.TclError:
        pytest.skip("No display available for Tk")
    window.geometry("1280x900")
    yield window
    window.destroy()


@pytest.fixture
def make_view(root, make_actions):
    """Factory: (view, calls) for shop.items, loaded.

    `stored` is the document list; extra DocumentPage fields can be passed.
    """
    def factory(stored=None, **overrides):
        stored = stored if stored is not None else []
        calls: list = []

        def add_documents(documents):
            stored.extend(documents)
            return ImportResult(len(documents), 0, list(stored))

        fields = dict(list_documents=lambda: list(stored),
                      add_documents=add_documents,
                      open_add_document=lambda: calls.append(("add",)))
        fields.update(overrides)
        page = DocumentPage("shop", "items", **fields)
        shell = make_shell(root, make_actions(calls))
        view = shell.show_page(lambda s: DocumentView(s, page))
        wait_for_load(root, view)
        return view, calls

    return factory


def schema_actions(schema=None) -> SchemaActions:
    store = {"schema": schema}
    return SchemaActions(
        get_schema=lambda: store["schema"],
        save_schema=lambda value: store.update(schema=value),
        remove_schema=lambda: store.update(schema=None),
        count_mismatches=lambda _value: 0)


def shown_documents(view) -> list[dict]:
    return [row.document for row in view.rows if row.winfo_manager()]


def test_page_lists_documents_and_counts_them(make_view) -> None:
    view, _calls = make_view([{"name": "pen"}, {"name": "cup"}])

    assert shown_documents(view) == [{"name": "pen"}, {"name": "cup"}]
    assert view.tabs["Documents"][0].cget("text") == "Documents  2"
    assert view.showing_label.cget("text") == "Showing 2 of 2 documents"


def test_page_shows_empty_message(make_view) -> None:
    view, _calls = make_view([])

    assert view.empty_label.winfo_manager() == "pack"
    assert view.showing_label.cget("text") == "Showing 0 of 0 documents"


def test_filter_hides_rows_that_dont_match(make_view) -> None:
    view, _calls = make_view([{"name": "pen"}, {"name": "cup"}])

    view.filter_entry.insert(0, "PEN")
    view.apply_filter()

    assert shown_documents(view) == [{"name": "pen"}]
    assert view.showing_label.cget("text") == "Showing 1 of 2 documents"


def test_add_document_button_opens_add_document_page(make_view) -> None:
    view, calls = make_view()

    view.page.open_add_document()

    assert calls == [("add",)]


# --- tabs ---


def test_schema_tab_hidden_without_schema_actions(make_view) -> None:
    view, _calls = make_view()

    assert list(view.tabs) == ["Documents"]
    assert view.schema_panel is None


def test_show_tab_swaps_panels_and_underline(make_view) -> None:
    view, _calls = make_view(schema=schema_actions())

    view.show_tab("Schema")

    assert view.schema_panel.winfo_manager() == "grid"
    assert not view.documents_panel.winfo_manager()
    assert view.active_tab == "Schema"
    label, _underline = view.tabs["Schema"]
    assert label.cget("text_color") == document_view.get_color("accent/primary")


def test_saving_schema_reloads_documents(root, make_view) -> None:
    view, _calls = make_view(schema=schema_actions())
    reloads: list = []
    view.refresh = lambda: reloads.append(1)
    view.schema_panel.on_change = view.refresh  # what _build_schema_panel set
    view.schema_panel.add_row().name.insert(0, "name")

    view.schema_panel.save()

    assert reloads == [1]


# --- schema mismatch markers ---


def test_documents_that_break_schema_are_marked(make_view) -> None:
    asked: list = []

    def find(ids):
        asked.append(ids)
        return {2}

    view, _calls = make_view([{"_id": 1}, {"_id": 2}], find_mismatches=find)

    assert asked == [[1, 2]]
    assert [row.broken for row in view.rows] == [False, True]
    assert view.showing_label.cget("text") == (
        "Showing 2 of 2 documents · 1 doesn't match the schema")


def test_status_counts_several_mismatches(make_view) -> None:
    view, _calls = make_view([{"_id": 1}, {"_id": 2}],
                             find_mismatches=lambda ids: {1, 2})

    assert view.showing_label.cget("text").endswith(
        "2 don't match the schema")


def test_no_markers_when_check_fails(make_view) -> None:
    from pymongo.errors import PyMongoError

    def fail(_ids):
        raise PyMongoError("down")

    view, _calls = make_view([{"_id": 1}], find_mismatches=fail)

    assert [row.broken for row in view.rows] == [False]


# --- import file ---


def test_import_file_adds_every_document_and_reloads(root, make_view,
                                                     tmp_path) -> None:
    path = tmp_path / "docs.json"
    path.write_text('[{"a": 1}, {"a": 2}]', encoding="utf-8")
    stored: list[dict] = []
    view, _calls = make_view(stored)
    view._choose_file = lambda: str(path)

    view.import_file()
    wait_for_load(root, view)

    assert stored == [{"a": 1}, {"a": 2}]
    assert view.showing_label.cget("text") == "Showing 2 of 2 documents"
    assert view.message_label.cget("text") == "Imported 2 documents."


def test_import_file_does_nothing_when_dialog_is_cancelled(make_view) -> None:
    stored: list[dict] = []
    view, _calls = make_view(stored)
    view._choose_file = lambda: ""

    view.import_file()

    assert stored == []
    assert view.message_label.cget("text") == ""


def test_import_file_shows_error_for_bad_json(make_view, tmp_path) -> None:
    path = tmp_path / "docs.json"
    path.write_text("{not json", encoding="utf-8")
    stored: list[dict] = []
    view, _calls = make_view(stored)
    view._choose_file = lambda: str(path)

    view.import_file()

    assert stored == []
    assert "Invalid JSON" in view.message_label.cget("text")


def test_preview_colors_keys_plain_and_values_green(make_view) -> None:
    view, _calls = make_view(stored=[{"name": "Alex", "age": 30}])
    preview = view.rows[0].preview

    def tags_at(word: str) -> tuple:
        start = preview.search(word, "1.0")
        return preview.tag_names(start)

    assert tags_at('"name"') == ("key",)
    assert tags_at('"Alex"') == ("string",)
    assert tags_at("30") == ("literal",)
    assert preview.tag_cget("key", "foreground") == \
        document_view.get_color("text/primary")
    assert preview.tag_cget("string", "foreground") == \
        preview.tag_cget("literal", "foreground") == \
        document_view.get_color("accent/primary")
    assert preview.cget("state") == "disabled"  # read-only


# --- document cards + Edit (Author: Archer) ---


def test_card_shows_indented_multiline_json(make_view) -> None:
    view, _calls = make_view(stored=[{"name": "Allen", "age": 30}])
    preview = view.rows[0].preview

    assert preview.get("1.0", "end-1c") == (
        '{\n  "name": "Allen",\n  "age": 30\n}')
    assert int(preview.cget("height")) >= 4  # every line visible


def test_filter_matches_text_inside_pretty_json(make_view) -> None:
    view, _calls = make_view([{"name": "pen"}, {"name": "cup"}])

    view.filter_entry.insert(0, '"name": "cup"')
    view.apply_filter()

    assert shown_documents(view) == [{"name": "cup"}]


def test_edit_button_opens_edit_page_with_the_document(make_view) -> None:
    edits: list = []
    view, _calls = make_view(stored=[{"_id": 1, "name": "pen"}],
                             open_edit_document=edits.append)

    view.rows[0].edit_button.invoke()

    assert edits == [{"_id": 1, "name": "pen"}]


def test_no_edit_button_without_edit_support(make_view) -> None:
    view, _calls = make_view(stored=[{"name": "pen"}])

    assert view.rows[0].edit_button is None


def test_broken_card_is_marked_and_keeps_edit(make_view) -> None:
    view, _calls = make_view(stored=[{"_id": 1}, {"_id": 2}],
                             find_mismatches=lambda ids: {2},
                             open_edit_document=lambda _doc: None)

    assert [row.broken for row in view.rows] == [False, True]
    assert view.rows[1].edit_button is not None
