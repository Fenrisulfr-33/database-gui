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
