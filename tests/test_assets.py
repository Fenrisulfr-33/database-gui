"""Tests for loading image files in gui/assets.py.

Author: Archer
"""

import tkinter as tk

import pytest

from db_gui.gui import assets


def test_brand_mark_file_exists() -> None:
    assert (assets.ASSETS_DIR / assets.BRAND_MARK).is_file()


def test_load_image_rejects_missing_file() -> None:
    with pytest.raises(FileNotFoundError, match="no_such_image.png"):
        assets.load_image("no_such_image.png", None)


def test_load_image_returns_brand_mark_at_design_size() -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("No display available for Tk")
    root.withdraw()
    try:
        image = assets.load_image(assets.BRAND_MARK, root)
        assert (image.width(), image.height()) == (26, 28)
    finally:
        root.destroy()
