"""Turn database values into text for the screen."""

from bson import json_util

PREVIEW_MAX_LENGTH = 120


def format_document_preview(document: dict, max_length: int = PREVIEW_MAX_LENGTH) -> str:
    """Return the document as one line of JSON, cut short if it is long."""
    text = json_util.dumps(document)
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."
