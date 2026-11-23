"""Turn database values into text for the screen."""

from bson import json_util

PREVIEW_MAX_LENGTH = 120


def format_document_preview(document: dict, max_length: int = PREVIEW_MAX_LENGTH) -> str:
    """Return the document as one line of JSON, cut short if it is long."""
    text = json_util.dumps(document)
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


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
