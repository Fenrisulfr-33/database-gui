"""Tests for the document view (needs a display, skipped without one)."""

import pytest

tk = pytest.importorskip("tkinter")

from db_gui.db.connection import ImportResult  # noqa: E402
from db_gui.gui.views import document_view  # noqa: E402


@pytest.fixture
def root():
    try:
        window = tk.Tk()
    except tk.TclError:
        pytest.skip("No display available for Tk")
    window.withdraw()
    yield window
    window.destroy()


def make_view(root, stored: list[dict], opened: list | None = None):
    """Make a DocumentView that uses a plain list instead of MongoDB."""
    opened = opened if opened is not None else []

    def add_documents(documents: list[dict]) -> ImportResult:
        stored.extend(documents)
        return ImportResult(len(documents), 0, list(stored))

    actions = document_view.DocumentActions(
        back=lambda: None,
        list_documents=lambda: list(stored),
        open_add_document=lambda: opened.append("add"),
        add_documents=add_documents,
    )
    return document_view.DocumentView(root, "shop.items", actions)


def _all_widgets(widget):
    for child in widget.winfo_children():
        yield child
        yield from _all_widgets(child)


def test_document_view_shows_existing_documents(root) -> None:
    view = make_view(root, [{"name": "pen"}])

    assert view._status_label.cget("text") == "1 document"


def test_add_document_button_opens_add_document_page(root) -> None:
    """Author: Archer (the pop-up became the Add document page)"""
    opened: list = []
    view = make_view(root, [], opened)
    button = next(widget for widget in _all_widgets(view)
                  if isinstance(widget, document_view.ctk.CTkButton)
                  and widget.cget("text") == "Add document")

    button.invoke()

    assert opened == ["add"]


# import file


def test_import_file_adds_every_document_and_refreshes(root, tmp_path) -> None:
    path = tmp_path / "docs.json"
    path.write_text('[{"a": 1}, {"a": 2}]', encoding="utf-8")
    stored: list[dict] = []
    view = make_view(root, stored)
    view._choose_file = lambda: str(path)

    view._import_file()

    assert stored == [{"a": 1}, {"a": 2}]
    assert view._status_label.cget("text") == "2 documents"
    assert view._message_label.cget("text") == "Imported 2 documents."


def test_import_file_does_nothing_when_dialog_is_cancelled(root) -> None:
    stored: list[dict] = []
    view = make_view(root, stored)
    view._choose_file = lambda: ""

    view._import_file()

    assert stored == []
    assert view._message_label.cget("text") == ""


def test_import_file_shows_error_for_bad_json(root, tmp_path) -> None:
    path = tmp_path / "docs.json"
    path.write_text("{not json", encoding="utf-8")
    stored: list[dict] = []
    view = make_view(root, stored)
    view._choose_file = lambda: str(path)

    view._import_file()

    assert stored == []
    assert "Invalid JSON" in view._message_label.cget("text")


# --- Schema mismatch markers (Author: Archer) ---


def make_marked_view(root, stored, find_mismatches):
    actions = document_view.DocumentActions(
        back=lambda: None,
        list_documents=lambda: list(stored),
        open_add_document=lambda: None,
        add_documents=lambda documents: ImportResult(0, 0, list(stored)),
        find_mismatches=find_mismatches,
    )
    return document_view.DocumentView(root, "shop.items", actions)


def marked_texts(view) -> list[str]:
    return [widget.cget("text") for widget in _all_widgets(view._document_list)
            if isinstance(widget, document_view.ctk.CTkLabel)
            and widget.cget("text") == document_view.BROKEN_LABEL]


def test_documents_that_break_schema_are_marked(root) -> None:
    asked: list = []

    def find(ids):
        asked.append(ids)
        return {2}

    view = make_marked_view(root, [{"_id": 1}, {"_id": 2}], find)

    assert asked == [[1, 2]]
    assert len(marked_texts(view)) == 1
    assert view._status_label.cget("text") == (
        "2 documents · 1 doesn't match the schema")


def test_status_counts_several_mismatches(root) -> None:
    view = make_marked_view(root, [{"_id": 1}, {"_id": 2}], lambda ids: {1, 2})

    assert view._status_label.cget("text") == (
        "2 documents · 2 don't match the schema")


def test_no_markers_when_check_fails(root) -> None:
    from pymongo.errors import PyMongoError

    def fail(_ids):
        raise PyMongoError("down")

    view = make_marked_view(root, [{"_id": 1}], fail)

    assert marked_texts(view) == []
    assert view._status_label.cget("text") == "1 document"


def test_no_markers_without_mismatch_check(root) -> None:
    view = make_view(root, [{"_id": 1}])

    assert marked_texts(view) == []
