"""Check user input before it goes to the database."""

import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from bson import Decimal128, Int64, ObjectId, json_util
from bson.errors import BSONError


def _loads(text: str):
    """Parse JSON, turning any error into a ValueError with a clear message."""
    try:
        return json_util.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Invalid JSON: {error.msg} "
            f"(line {error.lineno}, column {error.colno})."
        ) from error
    except (ValueError, TypeError, KeyError, BSONError) as error:
        raise ValueError(f"Invalid document: {error}") from error


def parse_document_json(text: str) -> dict:
    """Turn the text from the Add document box into a dict."""
    if not text.strip():
        raise ValueError("Enter a JSON document to add.")
    document = _loads(text)
    if not isinstance(document, dict):
        raise ValueError(
            'A document must be a JSON object, like {"name": "Ada"}.')
    return document


def _loads_json_lines(text: str, whole_file_error: ValueError):
    """Try reading the text as one JSON object per line."""
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        raise whole_file_error
    try:
        return [_loads(line) for line in lines]
    except ValueError:
        raise whole_file_error from None


def _as_document_list(data) -> list[dict]:
    """Make sure the data is an object or a list of objects."""
    if isinstance(data, dict):
        return [data]
    if not isinstance(data, list):
        raise ValueError(
            "The file must contain a JSON object or a list of objects.")
    if not data:
        raise ValueError("The file contains an empty list; nothing to import.")
    for position, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Item {position} is not a JSON object.")
    return data


def parse_documents_json(text: str) -> list[dict]:
    """Turn an imported file's text into a list of documents."""
    if not text.strip():
        raise ValueError("The file is empty.")
    try:
        data = _loads(text)
    except ValueError as whole_file_error:
        data = _loads_json_lines(text, whole_file_error)
    return _as_document_list(data)


# --- Schema form values (Author: Archer) ---
# The schema form (gui/widgets/schema_form.py) hands us the text typed into
# each input. These turn that text into the BSON type the schema expects,
# and check required + min/max, so bad values are caught (and marked red)
# before MongoDB rejects the document.

INT32_RANGE = (-2**31, 2**31 - 1)
INT64_RANGE = (-2**63, 2**63 - 1)
DATE_FORMAT = "%Y-%m-%d"  # e.g. 2026-11-23


def parse_field_value(field, text: str):
    """Turn one input's text into the field's type (one value, not a list).

    `field` is a db.schema.SchemaField. Empty text means "no value": an
    error for required fields, None (saved as null) for optional ones.
    Raises ValueError with a message to show under the input.

    Author: Archer
    """
    text = text.strip()
    if not text:
        if field.required and not field.is_array:
            raise ValueError("Required.")
        return None
    value = _convert(field.type, text)
    if not field.is_array:
        _check_range(field, value)
    return value


def parse_array_values(field, texts: list[str]) -> list:
    """Turn an array field's item texts into a list of the item type.

    Empty items are errors (arrays hold one strict type, no nulls). The
    list itself can be empty, unless min/max items says otherwise.

    Author: Archer
    """
    values = []
    for position, text in enumerate(texts, start=1):
        if not text.strip():
            raise ValueError(f"Item {position} is empty.")
        try:
            values.append(_convert(field.type, text.strip()))
        except ValueError as error:
            raise ValueError(f"Item {position}: {error}") from None
    _check_count(field, len(values), "items")
    return values


def parse_id_text(text: str):
    """The form's _id box: "" -> None (MongoDB makes one), 24 hex -> ObjectId,
    anything else stays a string.

    Author: Archer
    """
    text = text.strip()
    if not text:
        return None
    return ObjectId(text) if ObjectId.is_valid(text) else text


def _convert(type_name: str, text: str):
    """Text -> one BSON value of `type_name`. Raises ValueError.

    Author: Archer
    """
    converters = {
        "string": lambda value: value,
        "int": lambda value: _whole_number(value, INT32_RANGE),
        "long": lambda value: Int64(_whole_number(value, INT64_RANGE)),
        "double": _decimal_number,
        "decimal": _decimal128,
        "bool": _boolean,
        "date": _date,
        "objectId": _object_id,
    }
    return converters[type_name](text)


def _whole_number(text: str, limits: tuple[int, int]) -> int:
    """Author: Archer"""
    try:
        number = int(text)
    except ValueError:
        raise ValueError("Must be a whole number.") from None
    if not limits[0] <= number <= limits[1]:
        raise ValueError("Number is too big for this type.")
    return number


def _decimal_number(text: str) -> float:
    """Author: Archer"""
    try:
        number = float(text)
    except ValueError:
        raise ValueError("Must be a number.") from None
    if number != number or number in (float("inf"), float("-inf")):
        raise ValueError("Must be a number.")  # nan / inf
    return number


def _decimal128(text: str) -> Decimal128:
    """Author: Archer"""
    try:
        number = Decimal(text)
    except InvalidOperation:
        raise ValueError("Must be a number.") from None
    if not number.is_finite():
        raise ValueError("Must be a number.")
    return Decimal128(number)


def _boolean(text: str) -> bool:
    """Author: Archer"""
    if text.lower() not in ("true", "false"):
        raise ValueError("Must be true or false.")
    return text.lower() == "true"


def _date(text: str) -> datetime:
    """Author: Archer"""
    try:
        return datetime.strptime(text, DATE_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError:
        raise ValueError("Use the format YYYY-MM-DD, e.g. 2026-11-23.") from None


def _object_id(text: str) -> ObjectId:
    """Author: Archer"""
    if not ObjectId.is_valid(text):
        raise ValueError("Must be a 24-character hex ObjectId.")
    return ObjectId(text)


def _check_range(field, value) -> None:
    """Min/max: string length, or number value. Other types have none.

    Author: Archer
    """
    if field.type == "string":
        _check_count(field, len(value), "characters")
        return
    if field.type not in ("int", "long", "double", "decimal"):
        return
    number = value.to_decimal() if isinstance(value, Decimal128) else value
    if field.minimum is not None and number < field.minimum:
        raise ValueError(f"Must be at least {field.minimum}.")
    if field.maximum is not None and number > field.maximum:
        raise ValueError(f"Must be at most {field.maximum}.")


def _check_count(field, count: int, noun: str) -> None:
    """Min/max for a length (string characters or array items).

    Author: Archer
    """
    if field.minimum is not None and count < field.minimum:
        raise ValueError(f"Needs at least {field.minimum} {noun}.")
    if field.maximum is not None and count > field.maximum:
        raise ValueError(f"Allows at most {field.maximum} {noun}.")
