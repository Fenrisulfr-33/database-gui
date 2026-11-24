"""Load image files from src/db_gui/assets/ for use in the GUI.

Author: Archer (added the UI icon PNGs and set_icon)

Uses Tk's built-in PNG support (tk.PhotoImage), so no Pillow dependency.
Keep a reference to the returned image (e.g. on the widget or window that
shows it). Tk drops the picture if Python garbage-collects the object.
CustomTkinter widgets given `image=` keep that reference for you.

The icon PNGs are copied from design/ (same names, snake_case) and are
already sized/colored per the design, so they are shown as-is.
"""

import tkinter as tk
import warnings
from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
BRAND_MARK = "brand_mark.png"

# UI icons (16x16, except search at 14x14).
CHEVRON_DOWN = "chevron_down.png"  # green: an expanded Explorer database
CHEVRON_RIGHT = "chevron_right.png"  # grey: collapsed / "open this row"
ELLIPSIS = "ellipsis.png"  # a row's feature menu
REFRESH = "refresh_cw.png"
SEARCH = "search.png"
SLIDERS = "sliders_horizontal.png"  # "All databases" filter
TABLE = "table_2.png"  # a collection

# CustomTkinter warns whenever it gets a tk.PhotoImage instead of a CTkImage
# (CTkImage needs Pillow). Our icons are pixel-exact at their design size,
# so HighDPI scaling isn't needed; hide that one warning.
warnings.filterwarnings("ignore", message=r".*Given image is not CTkImage")


def load_image(file_name: str, master: tk.Misc) -> tk.PhotoImage:
    """Load a PNG/GIF from the assets folder as a Tk image.

    Author: Archer
    """
    path = ASSETS_DIR / file_name
    if not path.is_file():
        raise FileNotFoundError(f"Missing asset: {path}")
    return tk.PhotoImage(master=master, file=str(path))


def set_icon(widget, file_name: str) -> None:
    """Show an asset icon on a CTkButton/CTkLabel, left of any text.

    Author: Archer
    """
    widget.configure(image=load_image(file_name, widget), compound="left")


def make_icon_label(parent, file_name: str, background: str) -> tk.Label:
    """A borderless label showing just an asset icon (caller packs/grids).

    A plain tk.Label (not CTk) so it adds no padding around the image.

    Author: Archer
    """
    label = tk.Label(parent, borderwidth=0, background=background)
    label.image = load_image(file_name, label)  # keep a reference for Tk
    label.configure(image=label.image)
    return label
