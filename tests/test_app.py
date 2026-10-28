"""Tests for application messaging."""

from db_gui.gui.app import App


def test_rename_warning_explains_copy_and_recovery_in_plain_language() -> None:
    warning = App._build_rename_warning("old_name", "new_name", 2_500_000)

    assert "copy your database" in warning
    assert "remove the old one" in warning
    assert "about 2.5 MB" in warning
    assert "your original database will stay safe" in warning
    assert "MiB" not in warning


def test_rename_warning_explains_when_size_cannot_be_estimated() -> None:
    warning = App._build_rename_warning("old_name", "new_name", None)

    assert "couldn't estimate" in warning
    assert "your original database will stay safe" in warning
