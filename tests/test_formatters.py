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


# --- dashboard number formatting (Author: Archer) ---

def test_format_count_adds_commas_and_handles_missing() -> None:
    assert formatters.format_count(1284620) == "1,284,620"
    assert formatters.format_count(None) == formatters.MISSING_VALUE


def test_format_compact_count_shortens_big_numbers() -> None:
    assert formatters.format_compact_count(7_381_832) == "7.38M"
    assert formatters.format_compact_count(27) == "27"
    assert formatters.format_compact_count(None) == formatters.MISSING_VALUE


def test_format_bytes_picks_unit_and_precision() -> None:
    assert formatters.format_bytes(512) == "512 B"
    assert formatters.format_bytes(96_000) == "96.0 KB"
    assert formatters.format_bytes(842_600_000) == "842.6 MB"
    assert formatters.format_bytes(1_120_000_000) == "1.12 GB"
    assert formatters.format_bytes(None) == formatters.MISSING_VALUE


# --- Author: Archer ---


def test_format_document_pretty_indents_like_the_editor() -> None:
    text = formatters.format_document_pretty(
        {"_id": ObjectId("64a97a64b1fdc46c489253ef"), "first_name": "Allen"})

    assert text == ('{\n  "_id": {\n    "$oid": "64a97a64b1fdc46c489253ef"\n'
                    '  },\n  "first_name": "Allen"\n}')


def test_format_field_text_turns_values_into_form_text() -> None:
    import datetime

    midnight = datetime.datetime(2026, 11, 23)
    with_time = datetime.datetime(2026, 11, 23, 10, 30)

    assert formatters.format_field_text(None) == ""
    assert formatters.format_field_text(True) == "true"
    assert formatters.format_field_text(midnight) == "2026-11-23"
    assert formatters.format_field_text(with_time) == "2026-11-23T10:30:00"
    assert formatters.format_field_text(12) == "12"
