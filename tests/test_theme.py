"""Tests for the color palette lookup in gui/theme.py.

Author: Archer
"""

import pytest

from db_gui.gui import theme


@pytest.fixture(autouse=True)
def restore_palettes(monkeypatch: pytest.MonkeyPatch):
    """Give each test its own copy of PALETTES and reset the active palette."""
    monkeypatch.setattr(theme, "PALETTES", {
        name: dict(colors) for name, colors in theme.PALETTES.items()
    })
    yield
    theme._state["palette"] = theme.DEFAULT_PALETTE


def test_get_color_returns_hex_for_base_color() -> None:
    assert theme.get_color("accent/primary") == "#84d5a4"


def test_get_color_follows_aliases() -> None:
    # button/fill -> accent/primary, textbox/fill -> textbox/fill-login
    assert theme.get_color("button/fill") == theme.get_color("accent/primary")
    assert theme.get_color("textbox/fill") == "#404040"


def test_get_color_alias_updates_when_base_color_changes() -> None:
    theme.PALETTES["arrow_dark"]["accent/primary"] = "#123456"

    assert theme.get_color("button/fill") == "#123456"


def test_get_color_rejects_unknown_key() -> None:
    with pytest.raises(KeyError, match="no/such-color"):
        theme.get_color("no/such-color")


def test_get_color_rejects_alias_loop() -> None:
    theme.PALETTES["arrow_dark"]["loop/a"] = "loop/b"
    theme.PALETTES["arrow_dark"]["loop/b"] = "loop/a"

    with pytest.raises(ValueError, match="loop"):
        theme.get_color("loop/a")


def test_every_default_palette_key_resolves_to_hex() -> None:
    for key in theme.PALETTES[theme.DEFAULT_PALETTE]:
        assert theme.get_color(key).startswith("#")


def test_set_palette_switches_active_colors() -> None:
    theme.PALETTES["light_test"] = {"accent/primary": "#000000"}

    theme.set_palette("light_test")

    assert theme.get_active_palette_name() == "light_test"
    assert theme.get_color("accent/primary") == "#000000"


def test_set_palette_rejects_unknown_name() -> None:
    with pytest.raises(ValueError, match="Unknown palette"):
        theme.set_palette("missing")


def test_get_palette_names_lists_all_palettes() -> None:
    theme.PALETTES["another"] = {}

    assert theme.get_palette_names() == ["another", "arrow_dark"]
