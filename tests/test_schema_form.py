"""Tests for the schema form (needs a display, skipped without one).

Author: Archer
"""

import datetime

import pytest
from bson import ObjectId

tk = pytest.importorskip("tkinter")

from db_gui.db.schema import SchemaField  # noqa: E402
from db_gui.gui.widgets.schema_form import SchemaForm  # noqa: E402

FIELDS = [
    SchemaField("name", "string", required=True, minimum=1, maximum=20),
    SchemaField("age", "int", minimum=0),
    SchemaField("active", "bool", required=True),
    SchemaField("born", "date"),
    SchemaField("tags", "string", is_array=True, maximum=2),
]


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
def make_form(root):
    """Factory: (form, list of submit calls)."""
    def factory(fields=FIELDS):
        submits: list = []
        form = SchemaForm(root, fields, lambda: submits.append(1))
        return form, submits

    return factory


def by_name(form, name: str):
    return next(item for item in form.inputs if item.field.name == name)


def fill(form, **values) -> None:
    for name, text in values.items():
        by_name(form, name).entry.insert(0, text)


def test_form_has_id_box_first_then_one_input_per_field(make_form) -> None:
    form, _submits = make_form()

    assert [item.field.name for item in form.inputs] == [
        "_id", "name", "age", "active", "born", "tags"]


def test_form_skips_id_box_when_schema_defines_id(make_form) -> None:
    form, _submits = make_form([SchemaField("_id", "int", required=True)])

    assert [item.field.name for item in form.inputs] == ["_id"]


def test_get_document_converts_every_field(make_form) -> None:
    form, _submits = make_form()
    fill(form, name="Ada", age="36", born="2026-11-23")
    by_name(form, "tags").add_item("a")

    document = form.get_document()

    assert document == {
        "name": "Ada", "age": 36, "active": True,
        "born": datetime.datetime(2026, 11, 23, tzinfo=datetime.timezone.utc),
        "tags": ["a"],
    }


def test_get_document_saves_empty_optional_as_null(make_form) -> None:
    form, _submits = make_form()
    fill(form, name="Ada")

    document = form.get_document()

    assert document["age"] is None
    assert document["born"] is None
    assert document["tags"] == []
    assert "_id" not in document  # MongoDB generates one


def test_get_document_uses_typed_id(make_form) -> None:
    form, _submits = make_form()
    fill(form, _id="671d8e2f4a9b0c1234567890", name="Ada")

    assert form.get_document()["_id"] == ObjectId("671d8e2f4a9b0c1234567890")


def test_get_document_marks_every_bad_field_red(make_form) -> None:
    form, _submits = make_form()
    fill(form, age="-1", born="tomorrow")

    with pytest.raises(ValueError, match="marked in red"):
        form.get_document()

    assert by_name(form, "name").error.cget("text") == "Required."
    assert "at least 0" in by_name(form, "age").error.cget("text")
    assert "YYYY-MM-DD" in by_name(form, "born").error.cget("text")
    assert by_name(form, "name").entry.cget("border_color") != (
        by_name(form, "_id").entry.cget("border_color"))


def test_get_document_clears_errors_once_fixed(make_form) -> None:
    form, _submits = make_form()
    with pytest.raises(ValueError):
        form.get_document()

    fill(form, name="Ada")
    form.get_document()

    assert by_name(form, "name").error.cget("text") == ""
    assert not by_name(form, "name").error.winfo_manager()


def test_array_items_can_be_added_removed_and_checked(make_form) -> None:
    form, _submits = make_form()
    fill(form, name="Ada")
    tags = by_name(form, "tags")
    for text in ("a", "b", "c"):
        tags.add_item(text)

    with pytest.raises(ValueError):
        form.get_document()
    assert "at most 2 items" in tags.error.cget("text")

    tags._remove_item(tags.items[-1].master, tags.items[-1])
    assert form.get_document()["tags"] == ["a", "b"]


def test_optional_bool_offers_empty_choice(make_form) -> None:
    form, _submits = make_form([SchemaField("ok", "bool")])

    assert form.get_document() == {"ok": None}


def test_hint_describes_type_and_limits(make_form) -> None:
    form, _submits = make_form()

    assert by_name(form, "name").hint() == "string · required · 1–20 characters"
    assert by_name(form, "tags").hint() == "array of string · optional · max 2 items"
    assert by_name(form, "age").hint() == "int · optional · min 0"
    assert by_name(form, "born").hint() == "date · optional"
    assert "generate" in by_name(form, "_id").hint()


# --- fill (Edit page) (Author: Archer) ---


def test_fill_shows_values_and_returns_unknown_fields(make_form) -> None:
    form, _submits = make_form()

    extra = form.fill({"_id": 1, "name": "Ada", "active": True,
                       "born": datetime.datetime(2026, 11, 23),
                       "tags": ["a", "b"], "nickname": "A"})

    assert extra == ["nickname"]
    assert by_name(form, "name").entry.get() == "Ada"
    assert by_name(form, "active").entry.get() == "true"
    assert by_name(form, "born").entry.get() == "2026-11-23"
    assert [item.get() for item in by_name(form, "tags").items] == ["a", "b"]
    assert form.get_document()["_id"] == 1  # locked, original type


def test_fill_marks_wrong_types_red(make_form) -> None:
    form, _submits = make_form()

    form.fill({"_id": 1, "name": "Ada", "active": "yes", "age": "old"})

    assert by_name(form, "active").error.cget("text") == "Must be true or false."
    assert by_name(form, "age").error.cget("text") == "Must be a whole number."
