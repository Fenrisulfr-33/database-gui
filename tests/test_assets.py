"""Tests for loading image files in gui/assets.py.

Author: Archer (added tests for the UI icons, set_icon, make_icon_label)
"""

import tkinter as tk

import pytest

from db_gui.gui import assets


def test_brand_mark_file_exists() -> None:
    assert (assets.ASSETS_DIR / assets.BRAND_MARK).is_file()


def test_load_image_rejects_missing_file() -> None:
    with pytest.raises(FileNotFoundError, match="no_such_image.png"):
        assets.load_image("no_such_image.png", None)


@pytest.fixture
def tk_root():
    """A hidden Tk root, or skip when there's no display."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("No display available for Tk")
    root.withdraw()
    yield root
    root.destroy()


def test_load_image_returns_brand_mark_at_design_size(tk_root) -> None:
    image = assets.load_image(assets.BRAND_MARK, tk_root)
    assert (image.width(), image.height()) == (26, 28)


ICONS = [assets.CHEVRON_DOWN, assets.CHEVRON_RIGHT, assets.ELLIPSIS,
         assets.REFRESH, assets.SEARCH, assets.SLIDERS, assets.TABLE]


@pytest.mark.parametrize("icon", ICONS)
def test_load_image_loads_each_ui_icon(tk_root, icon) -> None:
    image = assets.load_image(icon, tk_root)
    assert image.width() in (14, 16)  # search is 14px, the rest 16px


def test_set_icon_puts_image_left_of_text(tk_root) -> None:
    import customtkinter as ctk  # local: only this test needs CTk

    button = ctk.CTkButton(tk_root, text="Refresh")
    assets.set_icon(button, assets.REFRESH)
    assert button.cget("image") is not None
    assert button.cget("compound") == "left"
    assert button.cget("text") == "Refresh"


def test_make_icon_label_keeps_image_reference(tk_root) -> None:
    label = assets.make_icon_label(tk_root, assets.TABLE, "#000000")
    assert label.cget("image") == str(label.image)
    assert label.cget("background") == "#000000"
