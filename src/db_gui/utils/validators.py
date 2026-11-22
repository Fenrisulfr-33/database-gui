"""Check user input before it goes to the database."""

import json

from bson import json_util
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
