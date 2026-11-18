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


def make_view(root, stored: list[dict]):
    """Make a DocumentView that uses a plain list instead of MongoDB."""
    def add_document(document: dict) -> list[dict]:
        stored.append(document)
        return list(stored)

    def add_documents(documents: list[dict]) -> ImportResult:
        stored.extend(documents)
        return ImportResult(len(documents), 0, list(stored))

    actions = document_view.DocumentActions(
        back=lambda: None,
        list_documents=lambda: list(stored),
        add_document=add_document,
        add_documents=add_documents,
    )
    return document_view.DocumentView(root, "shop.items", actions)


def test_document_view_shows_existing_documents(root) -> None:
    view = make_view(root, [{"name": "pen"}])

    assert view._status_label.cget("text") == "1 document"


def test_submit_document_adds_and_refreshes_list(root) -> None:
    stored: list[dict] = []
    view = make_view(root, stored)

    error = view._submit_document('{"name": "pen"}')

    assert error is None
    assert stored == [{"name": "pen"}]
    assert view._status_label.cget("text") == "1 document"


def test_submit_document_returns_error_for_bad_json(root) -> None:
    stored: list[dict] = []
    view = make_view(root, stored)

    error = view._submit_document("{not json")

    assert "Invalid JSON" in error
    assert stored == []


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
