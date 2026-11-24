"""Reusable stats table for the Dashboard (databases) and Collections pages,
styled after design/Dashboard.png and design/Collections.png.

Author: Archer (generalized from the dashboard's database table)

A TableConfig says what the columns are and what clicking does; the table
draws a header row, then one StatsRow per item: icon, name (+ optional
subtitle), the stat columns, a "···" feature menu, and a › chevron.
Items only need a `.name` attribute (DatabaseStats, CollectionStats, ...).

Author note: "···" and › are now the design's ellipsis / chevron-right PNGs,
and TableConfig.icon may be an icon file name (e.g. assets.TABLE) as well as
a draw_*_glyph function.
"""

import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass

import customtkinter as ctk

from ..assets import CHEVRON_RIGHT, ELLIPSIS, make_icon_label, set_icon
from ..theme import get_color
from .feature_menu import FeatureMenu, MenuItem
from .icons import create_icon_canvas
from .labels import make_label

SYSTEM_DATABASES = {"admin", "local", "config"}
MENU_COLUMN = 36  # width of the "···" column
OPEN_COLUMN = 32  # width of the › column


@dataclass
class TableConfig:
    """Columns + behavior for one StatsTable."""

    name_heading: str  # e.g. "DATABASE NAME ↓"
    headings: tuple  # stat column titles
    widths: tuple  # stat column widths (same length as headings)
    icon: Callable | str  # draw_*_glyph(canvas, color) or an icon file name
    values: Callable  # item -> tuple of display strings
    on_open: Callable  # item -> None (row click or ›)
    menu_items: Callable  # item -> list[MenuItem] for "···"
    subtitle: Callable = lambda _item: ""  # item -> grey line under name


def configure_columns(frame, config: TableConfig) -> None:
    """Give a header/row frame the shared column layout.

    Author: Archer
    """
    frame.grid_columnconfigure(0, weight=1)
    widths = (*config.widths, MENU_COLUMN, OPEN_COLUMN)
    for index, width in enumerate(widths, start=1):
        frame.grid_columnconfigure(index, minsize=width)


class StatsTable(ctk.CTkFrame):
    """Header row + scrollable list of StatsRow."""

    def __init__(self, master, config: TableConfig) -> None:
        """Author: Archer"""
        super().__init__(master, corner_radius=8, border_width=1,
                         fg_color=get_color("surface/card"),
                         border_color=get_color("border/default"))
        self._config = config
        self.rows: list[StatsRow] = []
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_heading()
        self._body = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0)
        self._body.grid(row=1, column=0, padx=2, pady=(0, 2), sticky="nsew")

    def _build_heading(self) -> None:
        """Column titles across the top.

        Author: Archer
        """
        heading = ctk.CTkFrame(self, fg_color="transparent")
        # Right padding matches the body's scrollbar so columns line up.
        heading.grid(row=0, column=0, padx=(18, 16), pady=(12, 10),
                     sticky="ew")
        configure_columns(heading, self._config)
        make_label(heading, self._config.name_heading, "column").grid(
            row=0, column=0, sticky="w")
        for index, title in enumerate(self._config.headings, start=1):
            make_label(heading, title, "column").grid(
                row=0, column=index, sticky="w")

    def set_items(self, items: list) -> None:
        """Replace all rows (in the given order).

        Author: Archer
        """
        for row in self.rows:
            row.destroy()
        self.rows = [StatsRow(self._body, item, self._config) for item in items]
        for row in self.rows:
            row.pack(fill="x")

    def apply_filter(self, text: str) -> int:
        """Hide rows whose name doesn't contain `text` (any case).

        Returns how many rows are still shown.

        Author: Archer
        """
        needle = text.strip().lower()
        for row in self.rows:
            row.pack_forget()
        # Re-pack matches in order so hidden rows don't leave gaps.
        shown = [row for row in self.rows if needle in row.name.lower()]
        for row in shown:
            row.pack(fill="x")
        return len(shown)


class StatsRow(ctk.CTkFrame):
    """One item: icon, name (+ subtitle), stats, "···", and ›."""

    def __init__(self, master, item, config: TableConfig) -> None:
        """Author: Archer"""
        super().__init__(master, corner_radius=0, fg_color="transparent",
                         cursor="hand2")
        self.item = item
        self.name = item.name
        self._config = config
        configure_columns(self, config)
        self._build_name_cell()
        for index, value in enumerate(config.values(item), start=1):
            self._bind_open(make_label(self, value, "body")).grid(
                row=0, column=index, sticky="w")
        self._build_buttons()
        # Thin divider under each row (tk.Frame: a 1px CTkFrame doesn't render).
        tk.Frame(self, height=1, background=get_color("border/default")).grid(
            row=1, column=0, columnspan=len(config.widths) + 3, sticky="ew")
        self._bind_open(self)

    def _build_name_cell(self) -> None:
        """Icon, name, and the optional subtitle.

        Author: Archer (icon can now be a PNG from assets)
        """
        cell = ctk.CTkFrame(self, fg_color="transparent")
        cell.grid(row=0, column=0, padx=(16, 0), pady=12, sticky="w")
        icon = self._make_icon(cell)
        icon.pack(side="left", padx=(0, 12))
        text = ctk.CTkFrame(cell, fg_color="transparent")
        text.pack(side="left")
        self._bind_open(make_label(text, self.name, "body")).pack(anchor="w")
        subtitle = self._config.subtitle(self.item)
        if subtitle:
            self._bind_open(make_label(text, subtitle, "muted")).pack(
                anchor="w", pady=(2, 0))
        for widget in (cell, icon, text):
            self._bind_open(widget)

    def _make_icon(self, parent):
        """The row's icon: a PNG label, or a canvas the glyph draws on.

        Author: Archer
        """
        background = get_color("surface/card")
        if isinstance(self._config.icon, str):
            return make_icon_label(parent, self._config.icon, background)
        canvas = create_icon_canvas(parent, 20, background)
        self._config.icon(canvas, get_color("text/secondary"))
        return canvas

    def _build_buttons(self) -> None:
        """The "···" feature menu button and the › open button.

        Author: Archer (both now use the design's icon PNGs)
        """
        common = {"text": "", "width": 28, "height": 28,
                  "fg_color": "transparent",
                  "hover_color": get_color("state/hover")}
        menu_column = len(self._config.widths) + 1
        self.more_button = ctk.CTkButton(self, command=self.show_menu,
                                         **common)
        set_icon(self.more_button, ELLIPSIS)
        self.more_button.grid(row=0, column=menu_column)
        self.open_button = ctk.CTkButton(self, command=self.open, **common)
        set_icon(self.open_button, CHEVRON_RIGHT)
        self.open_button.grid(row=0, column=menu_column + 1)

    def _bind_open(self, widget):
        """Make clicking `widget` open this item; returns the widget.

        Author: Archer
        """
        widget.bind("<Button-1>", lambda _event: self.open())
        return widget

    def open(self) -> None:
        """Author: Archer"""
        self._config.on_open(self.item)

    def build_menu_items(self) -> list[MenuItem]:
        """Features for this row's "···" menu (Close is added by the menu).

        Author: Archer
        """
        return self._config.menu_items(self.item)

    def show_menu(self) -> FeatureMenu:
        """Pop the styled feature menu up under "···".

        Author: Archer
        """
        return FeatureMenu(self.more_button, self.build_menu_items())
