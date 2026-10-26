"""Small vector icons drawn on a Tk canvas (no image files needed).

Author: Archer

Each draw_* function clears the canvas and redraws, so a toggle (like the
password eye) can simply call it again with different arguments.
"""

import tkinter as tk


def create_icon_canvas(parent, size: int, background: str) -> tk.Canvas:
    """Create a borderless square canvas that blends into its background.

    Author: Archer
    """
    return tk.Canvas(
        parent,
        width=size,
        height=size,
        background=background,
        highlightthickness=0,
        borderwidth=0,
    )


def draw_eye_glyph(canvas: tk.Canvas, color: str, crossed: bool) -> None:
    """Draw an eye; crossed=True adds a slash (meaning "hide password").

    Author: Archer
    """
    canvas.delete("all")
    size = int(canvas.cget("width"))
    mid = size / 2
    # Almond outline: smoothed polygon through the eye's corners and lids.
    canvas.create_polygon(
        size * 0.08, mid, mid, size * 0.2, size * 0.92, mid, mid, size * 0.8,
        smooth=True, fill="", outline=color, width=1.5,
    )
    pupil = size * 0.14
    canvas.create_oval(mid - pupil, mid - pupil, mid + pupil, mid + pupil,
                       outline=color, width=1.5)
    if crossed:
        canvas.create_line(size * 0.15, size * 0.85, size * 0.85, size * 0.15,
                           fill=color, width=1.5)
