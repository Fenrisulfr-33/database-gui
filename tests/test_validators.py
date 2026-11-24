"""Tests for utils/validators.py."""

import datetime

import pytest
from bson import ObjectId

from db_gui.utils import validators


def test_parse_document_json_returns_dict_for_plain_json() -> None:
    assert validators.parse_document_json('{"name": "Ada", "age": 36}') == {
        "name": "Ada", "age": 36}


def test_parse_document_json_accepts_nested_values() -> None:
    text = '{"tags": ["a", "b"], "address": {"city": "Denver"}}'

    assert validators.parse_document_json(text)["address"]["city"] == "Denver"


def test_parse_document_json_accepts_empty_object() -> None:
    assert validators.parse_document_json("{}") == {}


def test_parse_document_json_converts_extended_json_types() -> None:
    text = ('{"_id": {"$oid": "507f1f77bcf86cd799439011"}, '
            '"when": {"$date": "2026-11-11T00:00:00Z"}}')

    document = validators.parse_document_json(text)

    assert document["_id"] == ObjectId("507f1f77bcf86cd799439011")
    assert isinstance(document["when"], datetime.datetime)


@pytest.mark.parametrize("text", ["", "   ", "\n\n"])
def test_parse_document_json_rejects_blank_text(text: str) -> None:
    with pytest.raises(ValueError, match="Enter a JSON document"):
        validators.parse_document_json(text)


def test_parse_document_json_reports_line_and_column_for_bad_json() -> None:
    with pytest.raises(ValueError, match=r"Invalid JSON.*line 2"):
        validators.parse_document_json('{\n  "name": }')


@pytest.mark.parametrize("text", ["[1, 2]", '"hello"', "42", "null"])
def test_parse_document_json_rejects_non_objects(text: str) -> None:
    with pytest.raises(ValueError, match="JSON object"):
        validators.parse_document_json(text)


def test_parse_document_json_rejects_malformed_extended_json() -> None:
    with pytest.raises(ValueError, match="Invalid document"):
        validators.parse_document_json('{"_id": {"$oid": "not-an-id"}}')


# parse_documents_json


def test_parse_documents_json_wraps_single_object_in_list() -> None:
    assert validators.parse_documents_json('{"a": 1}') == [{"a": 1}]


def test_parse_documents_json_accepts_list_of_objects() -> None:
    text = '[{"a": 1}, {"a": 2}]'

    assert validators.parse_documents_json(text) == [{"a": 1}, {"a": 2}]


def test_parse_documents_json_accepts_json_lines() -> None:
    text = '{"a": 1}\n\n{"a": 2}\n'

    assert validators.parse_documents_json(text) == [{"a": 1}, {"a": 2}]


def test_parse_documents_json_converts_extended_json_in_lists() -> None:
    text = '[{"_id": {"$oid": "507f1f77bcf86cd799439011"}}]'

    assert validators.parse_documents_json(text)[0]["_id"] == ObjectId(
        "507f1f77bcf86cd799439011")


@pytest.mark.parametrize("text", ["", "  \n "])
def test_parse_documents_json_rejects_empty_file(text: str) -> None:
    with pytest.raises(ValueError, match="empty"):
        validators.parse_documents_json(text)


def test_parse_documents_json_rejects_empty_list() -> None:
    with pytest.raises(ValueError, match="empty list"):
        validators.parse_documents_json("[]")


def test_parse_documents_json_names_the_bad_item_in_a_list() -> None:
    with pytest.raises(ValueError, match="Item 2 is not a JSON object"):
        validators.parse_documents_json('[{"a": 1}, 5]')


@pytest.mark.parametrize("text", ['"hello"', "42", "null"])
def test_parse_documents_json_rejects_non_object_non_list(text: str) -> None:
    with pytest.raises(ValueError, match="object or a list"):
        validators.parse_documents_json(text)


def test_parse_documents_json_reports_whole_file_error_for_broken_json() -> None:
    with pytest.raises(ValueError, match="Invalid JSON"):
        validators.parse_documents_json('[{"a": 1},\n{"a": }]')


def test_parse_documents_json_rejects_json_lines_with_a_bad_line() -> None:
    with pytest.raises(ValueError, match="Invalid JSON"):
        validators.parse_documents_json('{"a": 1}\n{oops}')


# --- Schema form values (Author: Archer) ---

from bson import Decimal128, Int64  # noqa: E402

from db_gui.db.schema import SchemaField  # noqa: E402


@pytest.mark.parametrize("type_name, text, expected", [
    ("string", " Ada ", "Ada"),
    ("int", "42", 42),
    ("long", "5", Int64(5)),
    ("double", "2.5", 2.5),
    ("decimal", "19.99", Decimal128("19.99")),
    ("bool", "True", True),
    ("bool", "false", False),
    ("date", "2026-11-23",
     datetime.datetime(2026, 11, 23, tzinfo=datetime.timezone.utc)),
    ("objectId", "671d8e2f4a9b0c1234567890",
     ObjectId("671d8e2f4a9b0c1234567890")),
])
def test_parse_field_value_converts_to_schema_type(type_name, text, expected):
    value = validators.parse_field_value(SchemaField("a", type_name), text)

    assert value == expected
    assert type(value) is type(expected)


@pytest.mark.parametrize("type_name, text, message", [
    ("int", "4.5", "whole number"),
    ("int", str(2**31), "too big"),
    ("long", "x", "whole number"),
    ("double", "nan", "number"),
    ("double", "abc", "number"),
    ("decimal", "abc", "number"),
    ("decimal", "Infinity", "number"),
    ("bool", "yes", "true or false"),
    ("date", "23/11/2026", "YYYY-MM-DD"),
    ("objectId", "123", "hex ObjectId"),
])
def test_parse_field_value_rejects_bad_text(type_name, text, message) -> None:
    with pytest.raises(ValueError, match=message):
        validators.parse_field_value(SchemaField("a", type_name), text)


def test_parse_field_value_empty_required_is_error() -> None:
    with pytest.raises(ValueError, match="Required"):
        validators.parse_field_value(SchemaField("a", "string", True), "  ")


def test_parse_field_value_empty_optional_is_none() -> None:
    assert validators.parse_field_value(SchemaField("a", "int"), "") is None


@pytest.mark.parametrize("field, text, message", [
    (SchemaField("a", "string", minimum=3), "ab", "at least 3 characters"),
    (SchemaField("a", "string", maximum=2), "abc", "at most 2 characters"),
    (SchemaField("a", "int", minimum=0), "-1", "at least 0"),
    (SchemaField("a", "double", maximum=1.5), "2", "at most 1.5"),
    (SchemaField("a", "decimal", minimum=1), "0.5", "at least 1"),
])
def test_parse_field_value_checks_min_max(field, text, message) -> None:
    with pytest.raises(ValueError, match=message):
        validators.parse_field_value(field, text)


def test_parse_field_value_accepts_value_inside_limits() -> None:
    field = SchemaField("a", "int", minimum=0, maximum=10)

    assert validators.parse_field_value(field, "10") == 10


def test_parse_array_values_converts_each_item() -> None:
    field = SchemaField("tags", "int", is_array=True)

    assert validators.parse_array_values(field, ["1", " 2 "]) == [1, 2]


def test_parse_array_values_allows_empty_list() -> None:
    field = SchemaField("tags", "string", True, is_array=True)

    assert validators.parse_array_values(field, []) == []


@pytest.mark.parametrize("texts, message", [
    (["1", ""], "Item 2 is empty"),
    (["1", "x"], "Item 2: Must be a whole number"),
    ([], "at least 1 items"),
    (["1", "2", "3"], "at most 2 items"),
])
def test_parse_array_values_rejects_bad_items(texts, message) -> None:
    field = SchemaField("tags", "int", is_array=True, minimum=1, maximum=2)

    with pytest.raises(ValueError, match=message):
        validators.parse_array_values(field, texts)


@pytest.mark.parametrize("text, expected", [
    ("", None),
    ("671d8e2f4a9b0c1234567890", ObjectId("671d8e2f4a9b0c1234567890")),
    ("CUS-1", "CUS-1"),
])
def test_parse_id_text(text, expected) -> None:
    assert validators.parse_id_text(text) == expected


def test_parse_field_value_date_keeps_a_full_iso_time() -> None:
    field = SchemaField("born", "date")

    value = validators.parse_field_value(field, "2026-11-23T10:30:00")

    assert value == datetime.datetime(2026, 11, 23, 10, 30,
                                      tzinfo=datetime.timezone.utc)
