"""Tests for converting simplified schemas to/from $jsonSchema.

Author: Archer
"""

import pytest

from db_gui.db.schema import (SchemaField, UnsupportedSchemaError,
                              build_schema, parse_schema)


def test_build_schema_makes_strict_object_that_allows_id() -> None:
    schema = build_schema([SchemaField("name", "string", required=True)])

    assert schema == {
        "bsonType": "object",
        "additionalProperties": False,
        "properties": {"_id": {}, "name": {"bsonType": "string"}},
        "required": ["name"],
    }


def test_build_schema_optional_field_allows_null() -> None:
    schema = build_schema([SchemaField("age", "int")])

    assert schema["properties"]["age"] == {"bsonType": ["int", "null"]}
    assert "required" not in schema


def test_build_schema_array_holds_one_type_with_item_limits() -> None:
    field = SchemaField("tags", "string", required=True, is_array=True,
                        minimum=1, maximum=5)

    schema = build_schema([field])

    assert schema["properties"]["tags"] == {
        "bsonType": "array", "items": {"bsonType": "string"},
        "minItems": 1, "maxItems": 5,
    }


def test_build_schema_uses_length_for_strings_and_range_for_numbers() -> None:
    schema = build_schema([
        SchemaField("code", "string", True, minimum=2, maximum=4),
        SchemaField("price", "double", True, minimum=0.5),
    ])

    assert schema["properties"]["code"] == {
        "bsonType": "string", "minLength": 2, "maxLength": 4}
    assert schema["properties"]["price"] == {"bsonType": "double", "minimum": 0.5}


@pytest.mark.parametrize("fields, message", [
    ([SchemaField("", "string")], "needs a name"),
    ([SchemaField("$x", "string")], "can't start with"),
    ([SchemaField("a.b", "string")], "contain '.'"),
    ([SchemaField("a", "text")], "unknown type"),
    ([SchemaField("a", "int"), SchemaField("a", "string")], "Duplicate"),
    ([SchemaField("a", "bool", minimum=1)], "can't have a min/max"),
    ([SchemaField("a", "int", minimum=5, maximum=1)], "bigger than"),
    ([SchemaField("a", "string", minimum=-1)], "0 or more"),
    ([SchemaField("a", "string", maximum=2.5)], "whole numbers"),
    ([SchemaField("a", "int", minimum="1")], "must be numbers"),
])
def test_build_schema_rejects_invalid_fields(fields, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        build_schema(fields)


def test_parse_schema_round_trips_build_schema() -> None:
    fields = [
        SchemaField("name", "string", True, minimum=1, maximum=50),
        SchemaField("age", "int", minimum=0),
        SchemaField("born", "date"),
        SchemaField("scores", "double", True, is_array=True, maximum=10),
        SchemaField("owner", "objectId"),
    ]

    assert parse_schema(build_schema(fields)) == fields


def test_parse_schema_reads_typed_id_as_a_field() -> None:
    schema = {"bsonType": "object", "additionalProperties": False,
              "properties": {"_id": {"bsonType": "int"}}, "required": ["_id"]}

    assert parse_schema(schema) == [SchemaField("_id", "int", required=True)]


@pytest.mark.parametrize("schema, message", [
    ("nope", "JSON object"),
    ({"additionalProperties": False, "title": "x"}, "Unsupported"),
    ({"bsonType": "array", "additionalProperties": False}, "must be \"object\""),
    ({"properties": {}}, "strict"),
    ({"additionalProperties": False, "properties": []}, "properties"),
    ({"additionalProperties": False, "required": "a"}, "required"),
    ({"additionalProperties": False, "required": ["a"]}, "not defined"),
])
def test_parse_schema_rejects_unsupported_top_level(schema, message: str) -> None:
    with pytest.raises(UnsupportedSchemaError, match=message):
        parse_schema(schema)


def _schema_with(spec, required: bool = False) -> dict:
    schema = {"additionalProperties": False, "properties": {"a": spec}}
    if required:
        schema["required"] = ["a"]
    return schema


@pytest.mark.parametrize("spec, required, message", [
    ({"bsonType": "object"}, True, "unsupported type"),
    ({"bsonType": "string", "pattern": "^x"}, True, "pattern"),
    ({"bsonType": "string", "enum": ["x"]}, True, "enum"),
    ({"bsonType": ["string", "null"]}, True, "exactly one"),
    ({"bsonType": "string"}, False, "must allow null"),
    ({"bsonType": "array", "items": {"bsonType": "object"}}, True, "items"),
    ({"bsonType": "array", "items": [{"bsonType": "int"}]}, True, "items"),
    ({"bsonType": "array"}, True, "items"),
    ({"bsonType": "bool", "minimum": 1}, True, "minimum"),
    ({"bsonType": "int", "minimum": 5, "maximum": 1}, True, "bigger than"),
    ("string", True, "JSON object"),
])
def test_parse_schema_rejects_unsupported_fields(spec, required, message) -> None:
    with pytest.raises(UnsupportedSchemaError, match=message):
        parse_schema(_schema_with(spec, required))
