"""Small vector icons drawn on a Tk canvas (no image files needed).

Author: Archer (added the database, collection, pencil, and close glyphs)

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


def draw_database_glyph(canvas: tk.Canvas, color: str) -> None:
    """Draw a database "cylinder" (top ellipse, sides, two bands).

    Author: Archer
    """
    canvas.delete("all")
    size = int(canvas.cget("width"))
    left, right = size * 0.18, size * 0.82
    top, bottom = size * 0.12, size * 0.88
    band = size * 0.22  # height of each ellipse
    canvas.create_oval(left, top, right, top + band, outline=color, width=1.5)
    for y in (size * 0.45, bottom - band):
        # Lower half-ellipses mark the bands and the bottom edge.
        canvas.create_arc(left, y, right, y + band, start=180, extent=180,
                          style="arc", outline=color, width=1.5)
    mid_top = top + band / 2
    mid_bottom = bottom - band / 2
    canvas.create_line(left, mid_top, left, mid_bottom, fill=color, width=1.5)
    canvas.create_line(right, mid_top, right, mid_bottom, fill=color, width=1.5)


def draw_pencil_glyph(canvas: tk.Canvas, color: str) -> None:
    """Draw a slanted pencil outline (used for "Rename").

    Author: Archer
    """
    canvas.delete("all")
    s = int(canvas.cget("width"))
    # Body: a thin rotated rectangle from the tip (bottom-left) up-right.
    canvas.create_polygon(
        s * 0.12, s * 0.88, s * 0.18, s * 0.64, s * 0.70, s * 0.12,
        s * 0.88, s * 0.30, s * 0.36, s * 0.82,
        fill="", outline=color, width=1.6, joinstyle="round")
    # Line across the body where the eraser cap starts.
    canvas.create_line(s * 0.60, s * 0.22, s * 0.78, s * 0.40,
                       fill=color, width=1.6)


def draw_close_glyph(canvas: tk.Canvas, color: str) -> None:
    """Draw an X (used for "Close").

    Author: Archer
    """
    canvas.delete("all")
    s = int(canvas.cget("width"))
    low, high = s * 0.2, s * 0.8
    canvas.create_line(low, low, high, high, fill=color, width=1.8)
    canvas.create_line(low, high, high, low, fill=color, width=1.8)


def draw_collection_glyph(canvas: tk.Canvas, color: str) -> None:
    """Draw a small table (box with a header row and a column line).

    Author: Archer
    """
    canvas.delete("all")
    s = int(canvas.cget("width"))
    low, high = s * 0.15, s * 0.85
    canvas.create_rectangle(low, low, high, high, outline=color, width=1.4)
    canvas.create_line(low, s * 0.38, high, s * 0.38, fill=color, width=1.4)
    canvas.create_line(s * 0.40, s * 0.38, s * 0.40, high, fill=color,
                       width=1.4)
