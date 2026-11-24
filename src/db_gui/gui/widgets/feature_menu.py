"""The "···" database feature menu, styled after design/Database features.png.

Author: Archer

A small borderless card that pops up under the "···" button: one row per
feature (icon + label, green highlight on hover), a divider, then Close.
It closes on Close, Esc, a click outside it, or after running a feature.

To add a feature, add a MenuItem to the page's TableConfig.menu_items
(views/dashboard_view.py or views/collections_view.py) and an icon here in
ICONS if it needs a new one.
"""

import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass

import customtkinter as ctk

from ..theme import get_color, get_font
from .icons import create_icon_canvas, draw_close_glyph, draw_pencil_glyph

MENU_WIDTH = 200
ICON_SIZE = 18
# icon name -> (draw function, palette color key)
ICONS = {
    "rename": (draw_pencil_glyph, "accent/primary"),
    "close": (draw_close_glyph, "text/secondary"),
}


@dataclass
class MenuItem:
    """One feature row: its label, an ICONS key, and what it runs."""

    label: str
    icon: str
    command: Callable[[], None]


class FeatureMenu(ctk.CTkToplevel):
    """Pop-up list of features under `anchor`, then a Close row."""

    def __init__(self, anchor, items: list[MenuItem]) -> None:
        """Author: Archer"""
        super().__init__(anchor, fg_color=get_color("surface/card"))
        self.overrideredirect(True)
        # A Toplevel ignores border_width, so draw the 1px border with Tk's
        # highlight ring instead.
        border = get_color("border/default")
        self.configure(highlightthickness=1, highlightbackground=border,
                       highlightcolor=border)
        self.rows = [self._add_row(item) for item in items]
        # Divider between the features and Close (tk.Frame: a 1px
        # CTkFrame doesn't render).
        tk.Frame(self, height=1, background=get_color("border/default")).pack(
            fill="x", padx=1)
        self.rows.append(self._add_row(MenuItem("Close", "close", lambda: None)))
        self.bind("<Escape>", lambda _event: self.close())
        self.bind("<ButtonPress-1>", self._close_if_outside)
        self._place_under(anchor)
        # grab_set fails until the window is shown, so wait a moment.
        self.after(50, self._grab)

    def _add_row(self, item: MenuItem) -> ctk.CTkFrame:
        """Icon + label row that highlights green while hovered.

        Author: Archer
        """
        row = ctk.CTkFrame(self, corner_radius=8, fg_color="transparent",
                           cursor="hand2")
        row.pack(fill="x", padx=8, pady=6)
        draw, color_key = ICONS[item.icon]
        icon = create_icon_canvas(row, ICON_SIZE, get_color("surface/card"))
        draw(icon, get_color(color_key))
        icon.pack(side="left", padx=(12, 14), pady=10)
        text_key = "text/secondary" if item.icon == "close" else "text/primary"
        label = ctk.CTkLabel(row, text=item.label, font=get_font(13),
                             text_color=get_color(text_key), height=0)
        label.pack(side="left")
        row.icon = icon  # kept so hover can recolor the canvas background
        for widget in (row, icon, label):
            widget.bind("<Enter>", lambda _e, r=row: self._highlight(r, True))
            widget.bind("<Leave>", lambda e, r=row: self._leave(r, e))
            widget.bind("<ButtonRelease-1>",
                        lambda _e, i=item: self._run(i.command))
        return row

    def _highlight(self, row, on: bool) -> None:
        """Green background on hover, back to the card color after.

        Author: Archer
        """
        color = get_color("accent/subtle") if on else get_color("surface/card")
        row.configure(fg_color=color if on else "transparent")
        row.icon.configure(background=color)

    def _leave(self, row, event) -> None:
        """Only un-highlight when the pointer really left the row (moving
        onto the row's own icon or label also fires <Leave>).

        Author: Archer
        """
        under = row.winfo_containing(event.x_root, event.y_root)
        if under is None or not str(under).startswith(str(row)):
            self._highlight(row, False)

    def _place_under(self, anchor) -> None:
        """Line the menu's right edge up with the anchor, just below it.

        Author: Archer
        """
        self.update_idletasks()
        height = self.winfo_reqheight()
        x = anchor.winfo_rootx() + anchor.winfo_width() - MENU_WIDTH
        y = anchor.winfo_rooty() + anchor.winfo_height() + 4
        # Flip above the button if it would run off the bottom of the screen.
        if y + height > self.winfo_screenheight():
            y = anchor.winfo_rooty() - height - 4
        self.geometry(f"{MENU_WIDTH}x{height}+{max(x, 0)}+{max(y, 0)}")

    def _grab(self) -> None:
        """Send all clicks here so a click outside can close the menu.

        Author: Archer
        """
        if self.winfo_exists():
            self.lift()
            self.focus_force()
            try:
                self.grab_set()
            except Exception:  # noqa: BLE001 - grab is a nicety, not required
                pass

    def _close_if_outside(self, event) -> None:
        """While grabbed, a click anywhere else in the app closes the menu.

        Author: Archer
        """
        inside = (0 <= event.x_root - self.winfo_rootx() < self.winfo_width()
                  and 0 <= event.y_root - self.winfo_rooty()
                  < self.winfo_height())
        if not inside:
            self.close()

    def _run(self, command: Callable[[], None]) -> None:
        """Close first (so a feature's own pop-up isn't stuck behind the
        menu's grab), then run the feature.

        Author: Archer
        """
        self.close()
        command()

    def close(self) -> None:
        """Author: Archer"""
        if self.winfo_exists():
            self.grab_release()
            self.destroy()
