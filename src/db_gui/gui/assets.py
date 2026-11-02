"""Load image files from src/db_gui/assets/ for use in the GUI.

Author: Archer

Uses Tk's built-in PNG support (tk.PhotoImage), so no Pillow dependency.
Keep a reference to the returned image (e.g. on the widget or window that
shows it). Tk drops the picture if Python garbage-collects the object.
"""

import tkinter as tk
from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
BRAND_MARK = "brand_mark.png"


def load_image(file_name: str, master: tk.Misc) -> tk.PhotoImage:
    """Load a PNG/GIF from the assets folder as a Tk image.

    Author: Archer
    """
    path = ASSETS_DIR / file_name
    if not path.is_file():
        raise FileNotFoundError(f"Missing asset: {path}")
    return tk.PhotoImage(master=master, file=str(path))
