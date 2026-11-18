"""Tests for utils/formatters.py."""

from bson import ObjectId

from db_gui.utils import formatters


def test_format_document_preview_returns_short_documents_unchanged() -> None:
    assert formatters.format_document_preview({"a": 1}) == '{"a": 1}'


def test_format_document_preview_truncates_long_documents() -> None:
    preview = formatters.format_document_preview({"text": "x" * 500}, 50)

    assert len(preview) == 50
    assert preview.endswith("...")


def test_format_document_preview_handles_object_ids() -> None:
    preview = formatters.format_document_preview(
        {"_id": ObjectId("507f1f77bcf86cd799439011")})

    assert "507f1f77bcf86cd799439011" in preview
