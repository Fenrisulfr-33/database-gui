"""Tests for utils/files.py."""

from pathlib import Path

import pytest

from db_gui.utils import files


def test_read_text_file_returns_contents(tmp_path: Path) -> None:
    path = tmp_path / "docs.json"
    path.write_text('{"a": 1}', encoding="utf-8")

    assert files.read_text_file(str(path)) == '{"a": 1}'


def test_read_text_file_ignores_windows_bom(tmp_path: Path) -> None:
    path = tmp_path / "docs.json"
    path.write_bytes(b"\xef\xbb\xbf" + b'{"a": 1}')

    assert files.read_text_file(str(path)) == '{"a": 1}'


def test_read_text_file_reports_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Could not read the file"):
        files.read_text_file(str(tmp_path / "nope.json"))


def test_read_text_file_rejects_non_utf8(tmp_path: Path) -> None:
    path = tmp_path / "docs.json"
    path.write_bytes(b"\xff\xfe\x00\x00 not utf8 \x80")

    with pytest.raises(ValueError, match="not UTF-8"):
        files.read_text_file(str(path))


def test_read_text_file_rejects_oversized_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "docs.json"
    path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(files, "MAX_IMPORT_BYTES", 1)

    with pytest.raises(ValueError, match="larger than"):
        files.read_text_file(str(path))
