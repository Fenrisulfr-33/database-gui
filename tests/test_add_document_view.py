"""Tests for the Add document page (needs a display, skipped without one).

Author: Archer
"""

import pytest

tk = pytest.importorskip("tkinter")

from conftest import wait_for_load  # noqa: E402
from db_gui.db.schema import UnsupportedSchemaError  # noqa: E402
from db_gui.gui.views import add_document_view  # noqa: E402
from db_gui.gui.views.add_document_view import (AddDocumentPage,  # noqa: E402
                                                AddDocumentView)
from db_gui.utils.saved_clusters import SavedCluster  # noqa: E402


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
    """Factory: (view, calls, stored) for shop.customers, loaded.

    `add_document` / `get_schema` can be swapped in.
    """
    def factory(add_document=None, get_schema=lambda: None):
        calls: list = []
        stored: list[dict] = []

        def store(document: dict) -> list[dict]:
            stored.append(document)
            return list(stored)

        page = AddDocumentPage("shop", "customers", add_document or store,
                               get_schema)
        login = SavedCluster("c0.example.net", "admin", "pw", "Work")
        view = AddDocumentView(root, login, (make_actions(calls), page))
        wait_for_load(root, view)
        return view, calls, stored

    return factory


def test_page_starts_ready_with_template(make_view) -> None:
    view, _calls, _stored = make_view()

    assert view.insert_button.cget("state") == "normal"
    assert "ready to insert" in view.ready_label.cget("text")


def test_invalid_json_disables_insert(make_view) -> None:
    view, _calls, _stored = make_view()

    view.editor.set_text("{oops")

    assert view.insert_button.cget("state") == "disabled"
    assert "Fix the JSON" in view.ready_label.cget("text")


def test_insert_document_adds_and_goes_back(make_view) -> None:
    view, calls, stored = make_view()
    view.editor.set_text('{"name": "Ada"}')

    view.insert_document()

    assert stored == [{"name": "Ada"}]
    assert calls == [("open_collection", "shop", "customers")]


def test_insert_document_shows_rejection_and_stays(make_view) -> None:
    def reject(_document):
        raise ValueError("A document with that _id already exists.")

    view, calls, _stored = make_view(add_document=reject)

    view.insert_document()

    assert calls == []
    assert view.ready_label.cget("text") == (
        "A document with that _id already exists.")


def test_insert_document_reports_server_error(make_view) -> None:
    from pymongo.errors import PyMongoError

    def fail(_document):
        raise PyMongoError("denied")

    view, calls, _stored = make_view(add_document=fail)

    view.insert_document()

    assert calls == []
    assert "Check your permissions" in view.ready_label.cget("text")


def test_shortcut_inserts_only_when_valid(make_view) -> None:
    view, _calls, stored = make_view()
    view.editor.set_text("{oops")

    assert view._on_shortcut() == "break"
    assert stored == []

    view.editor.set_text('{"a": 1}')
    view._on_shortcut()
    assert stored == [{"a": 1}]


def test_go_back_opens_documents(make_view) -> None:
    view, calls, _stored = make_view()

    view.go_back()

    assert calls == [("open_collection", "shop", "customers")]


@pytest.mark.parametrize("get_schema, expected", [
    (lambda: None, False),
    (lambda: {"bsonType": "object"}, True),
])
def test_schema_line_shows_whether_schema_is_enforced(
        make_view, get_schema, expected) -> None:
    view, _calls, _stored = make_view(get_schema=get_schema)

    assert view.schema_label.cget("text") == (
        add_document_view.SCHEMA_TEXTS[expected])


def test_unsupported_validator_still_counts_as_schema(make_view) -> None:
    def unsupported():
        raise UnsupportedSchemaError("query rules")

    view, _calls, _stored = make_view(get_schema=unsupported)

    assert view.schema_label.cget("text") == add_document_view.SCHEMA_TEXTS[True]


def test_namespace_is_database_dot_collection(make_view) -> None:
    view, _calls, _stored = make_view()

    assert view._namespace() == "shop.customers"


# --- Schema form (Author: Archer) ---

from db_gui.db.schema import SchemaField, build_schema  # noqa: E402

NAME_SCHEMA = build_schema([SchemaField("name", "string", required=True)])


def test_page_uses_form_when_collection_has_schema(make_view) -> None:
    view, _calls, _stored = make_view(get_schema=lambda: NAME_SCHEMA)

    assert view.form is not None
    assert not view.editor.winfo_manager()  # JSON editor hidden
    assert view.types_label.cget("text") == add_document_view.FORM_TYPES_TEXT
    assert "Fill in the fields" in view.ready_label.cget("text")
    assert not view.json_link.winfo_manager()


def test_page_keeps_json_editor_without_schema(make_view) -> None:
    view, _calls, _stored = make_view()

    assert view.form is None
    assert view.editor.winfo_manager() == "grid"


def test_form_insert_adds_converted_document(make_view) -> None:
    view, calls, stored = make_view(get_schema=lambda: NAME_SCHEMA)
    view.form.inputs[1].entry.insert(0, "Ada")

    view.insert_document()

    assert stored == [{"name": "Ada"}]
    assert calls == [("open_collection", "shop", "customers")]


def test_form_insert_refuses_bad_fields(make_view) -> None:
    view, calls, stored = make_view(get_schema=lambda: NAME_SCHEMA)

    view._on_shortcut()

    assert stored == []
    assert calls == []
    assert view.ready_label.cget("text") == "Fix the fields marked in red."


def test_refresh_keeps_the_same_form(root, make_view) -> None:
    view, _calls, _stored = make_view(get_schema=lambda: NAME_SCHEMA)
    form = view.form
    form.inputs[1].entry.insert(0, "typed")

    view.refresh()
    wait_for_load(root, view)

    assert view.form is form
    assert form.inputs[1].entry.get() == "typed"
