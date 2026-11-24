"""Turn database values into text for the screen.

Author note (Archer): added format_document_pretty() (indented JSON for the
document cards) and format_field_text() (fills the schema form when editing).
"""

from datetime import datetime

from bson import json_util

PREVIEW_MAX_LENGTH = 120


def format_document_preview(document: dict, max_length: int = PREVIEW_MAX_LENGTH) -> str:
    """Return the document as one line of JSON, cut short if it is long."""
    text = json_util.dumps(document)
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def format_document_pretty(document: dict) -> str:
    """The document as indented, multi-line Extended JSON (2 spaces), the
    way the JSON editor shows it. ObjectIds show as {"$oid": "..."} and
    dates as {"$date": "..."}, which the editor can read back.

    Author: Archer
    """
    return json_util.dumps(document, indent=2, ensure_ascii=False)


def format_field_text(value) -> str:
    """One stored value as the text a schema-form box should start with
    (the reverse of utils/validators.py parse_field_value).

    None -> "" (empty box), bools -> "true" / "false", dates at midnight ->
    "YYYY-MM-DD" (with a time -> full ISO, so editing doesn't drop it),
    everything else (text, numbers, ObjectId, Decimal128) -> str(value).
    A value of the wrong type still comes out as text, so the form can mark
    it red when it's checked.

    Author: Archer
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, datetime):
        if value.time() == datetime.min.time():
            return value.strftime("%Y-%m-%d")
        return value.isoformat()
    return str(value)


# Shown wherever the server didn't give us a number.
MISSING_VALUE = "—"
_BYTE_UNITS = ("B", "KB", "MB", "GB", "TB")
_COMPACT_UNITS = ((1_000_000_000, "B"), (1_000_000, "M"), (1_000, "K"))


def format_count(value: int | None) -> str:
    """1284620 -> "1,284,620" (dashboard table cells).

    Author: Archer
    """
    return MISSING_VALUE if value is None else f"{value:,}"


def format_compact_count(value: int | None) -> str:
    """7381832 -> "7.38M", 27 -> "27" (dashboard stat cards).

    Author: Archer
    """
    if value is None:
        return MISSING_VALUE
    for size, suffix in _COMPACT_UNITS:
        if value >= size:
            return f"{value / size:.2f}{suffix}"
    return str(value)


def format_bytes(value: int | None) -> str:
    """842600000 -> "842.6 MB", 1120000000 -> "1.12 GB" (decimal units).

    GB and up get two decimals to match design/Dashboard.png.

    Author: Archer
    """
    if value is None:
        return MISSING_VALUE
    amount = float(value)
    unit_index = 0
    while amount >= 1000 and unit_index < len(_BYTE_UNITS) - 1:
        amount /= 1000
        unit_index += 1
    if unit_index == 0:
        return f"{int(amount)} B"
    decimals = 2 if unit_index >= 3 else 1
    return f"{amount:.{decimals}f} {_BYTE_UNITS[unit_index]}"
