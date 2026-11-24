"""Tests for the Schema tab (needs a display, skipped without one).

Author: Archer
"""

import json

import pytest

tk = pytest.importorskip("tkinter")

from db_gui.db.schema import SchemaField, build_schema  # noqa: E402
from db_gui.gui.widgets import schema_tab  # noqa: E402

NAME_SCHEMA = build_schema([SchemaField("name", "string", required=True)])


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
def answers(monkeypatch):
    """Record pop-ups instead of showing them; answer with answers[0]."""
    replies = [True]
    shown = []

    def fake_dialog(_parent, spec):
        shown.append(spec)
        return replies[0]

    monkeypatch.setattr(schema_tab, "show_dialog", fake_dialog)
    return replies, shown


def make_tab(root, schema=None, mismatches=0):
    """A SchemaTab whose actions use a dict instead of MongoDB."""
    store = {"schema": schema}
    actions = schema_tab.SchemaActions(
        get_schema=lambda: store["schema"],
        save_schema=lambda value: store.update(schema=value),
        remove_schema=lambda: store.update(schema=None),
        count_mismatches=lambda _value: mismatches,
    )
    return schema_tab.SchemaTab(root, actions), store


def test_load_schema_without_schema_shows_hint_and_disables_remove(root) -> None:
    tab, _store = make_tab(root)

    assert tab.rows == []
    assert "no schema yet" in tab.message.cget("text")
    assert tab.remove_button.cget("state") == "disabled"


def test_load_schema_fills_simplified_rows(root) -> None:
    tab, _store = make_tab(root, NAME_SCHEMA)

    assert [row.to_field() for row in tab.rows] == [
        SchemaField("name", "string", required=True)]
    assert tab.remove_button.cget("state") == "normal"


def test_load_schema_opens_unsupported_schema_in_raw_json(root) -> None:
    schema = dict(NAME_SCHEMA, title="extra")

    tab, _store = make_tab(root, schema)

    assert tab.view == schema_tab.RAW_JSON
    assert "Unsupported" in tab.message.cget("text")
    assert json.loads(tab.json_box.get("1.0", "end")) == schema


def test_save_builds_schema_from_rows(root, answers) -> None:
    tab, store = make_tab(root)
    row = tab.add_row()
    row.name.insert(0, "age")
    row.type.set("int")
    row.minimum.insert(0, "0")

    tab.save()

    assert store["schema"] == build_schema([SchemaField("age", "int", minimum=0)])
    assert tab.message.cget("text") == "Schema saved."
    assert answers[1] == []  # no documents broke it, so no warning


def test_save_without_fields_is_refused(root) -> None:
    tab, store = make_tab(root)

    tab.save()

    assert store["schema"] is None
    assert "at least one field" in tab.message.cget("text")


def test_save_reports_bad_limit(root) -> None:
    tab, store = make_tab(root)
    row = tab.add_row()
    row.name.insert(0, "age")
    row.minimum.insert(0, "lots")

    tab.save()

    assert store["schema"] is None
    assert "must be a number" in tab.message.cget("text")


def test_save_warns_about_mismatches_and_can_cancel(root, answers) -> None:
    replies, shown = answers
    replies[0] = False
    tab, store = make_tab(root, mismatches=3)
    tab.add_row().name.insert(0, "name")

    tab.save()

    assert store["schema"] is None
    assert shown[0].heading == "3 documents don't match this schema."


def test_save_warns_about_mismatches_and_can_save_anyway(root, answers) -> None:
    tab, store = make_tab(root, mismatches=1)
    tab.add_row().name.insert(0, "name")

    tab.save()

    assert store["schema"] is not None
    assert answers[1][0].heading == "1 document doesn't match this schema."


def test_switch_view_copies_rows_into_json_and_back(root) -> None:
    tab, _store = make_tab(root, NAME_SCHEMA)

    tab._switch_view(schema_tab.RAW_JSON)
    assert json.loads(tab.json_box.get("1.0", "end")) == NAME_SCHEMA

    edited = build_schema([SchemaField("tags", "string", is_array=True)])
    tab._set_json(edited)
    tab._switch_view(schema_tab.SIMPLIFIED)

    assert [row.to_field() for row in tab.rows] == [
        SchemaField("tags", "string", is_array=True)]


def test_switch_view_stays_put_on_bad_json(root) -> None:
    tab, _store = make_tab(root)
    tab._switch_view(schema_tab.RAW_JSON)
    tab.json_box.insert("1.0", "{not json")

    tab._switch_view(schema_tab.SIMPLIFIED)

    assert tab.view == schema_tab.RAW_JSON
    assert tab.toggle.get() == schema_tab.RAW_JSON
    assert "Invalid JSON" in tab.message.cget("text")


def test_save_from_raw_json_rejects_unsupported(root, answers) -> None:
    tab, store = make_tab(root)
    tab._switch_view(schema_tab.RAW_JSON)
    tab._set_json(dict(NAME_SCHEMA, title="extra"))

    tab.save()

    assert store["schema"] is None
    assert "Unsupported" in tab.message.cget("text")


def test_save_from_raw_json_saves_edited_schema(root, answers) -> None:
    tab, store = make_tab(root)
    tab._switch_view(schema_tab.RAW_JSON)
    tab._set_json(NAME_SCHEMA)

    tab.save()

    assert store["schema"] == NAME_SCHEMA
    assert tab.remove_button.cget("state") == "normal"


def test_remove_asks_then_clears_schema(root, answers) -> None:
    tab, store = make_tab(root, NAME_SCHEMA)

    tab.remove()

    assert store["schema"] is None
    assert tab.remove_button.cget("state") == "disabled"
    assert answers[1][0].title == "Remove schema"


def test_remove_keeps_schema_when_cancelled(root, answers) -> None:
    answers[0][0] = False
    tab, store = make_tab(root, NAME_SCHEMA)

    tab.remove()

    assert store["schema"] == NAME_SCHEMA


def test_remove_row_drops_it(root) -> None:
    tab, _store = make_tab(root, NAME_SCHEMA)

    tab._remove_row(tab.rows[0])

    assert tab.rows == []


def test_save_and_remove_notify_documents_screen(root, answers) -> None:
    """Author: Archer"""
    tab, _store = make_tab(root)
    changes: list = []
    tab.on_change = lambda: changes.append(1)
    tab.add_row().name.insert(0, "name")

    tab.save()
    tab.remove()

    assert changes == [1, 1]


def test_failed_save_does_not_notify(root) -> None:
    """Author: Archer"""
    tab, _store = make_tab(root)
    changes: list = []
    tab.on_change = lambda: changes.append(1)

    tab.save()  # no fields -> refused

    assert changes == []
