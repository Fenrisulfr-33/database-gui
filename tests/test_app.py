"""Tests for application messaging."""

from db_gui.gui.app import App


def test_rename_warning_explains_local_archive_and_recovery() -> None:
    warning = App._build_rename_warning("old_name", "new_name", 2_500_000)

    assert "temporary BSON archive" in warning
    assert "before removing the old database" in warning
    assert "local disk space" in warning
    assert "about 2.5 MB" in warning
    assert "automatic recovery fails" in warning
    assert "may not immediately reduce its reported allocated storage" in warning
    assert "MiB" not in warning


def test_rename_warning_explains_when_size_cannot_be_estimated() -> None:
    warning = App._build_rename_warning("old_name", "new_name", None)

    assert "couldn't estimate how much local disk space is needed" in warning
