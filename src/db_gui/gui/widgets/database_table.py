"""Dashboard table of databases with their stats, styled after
design/Dashboard.png.

Author: Archer

Columns: name, collections, documents, data size, storage size, a "···"
feature menu (Rename + Close, see feature_menu.py), and a › chevron. Clicking a row (or ›) opens
the database. `actions` is the dashboard's DashboardActions.
"""

import tkinter as tk

import customtkinter as ctk

from ...utils.formatters import format_bytes, format_count
from ..theme import get_color, get_font
from .feature_menu import FeatureMenu, MenuItem
from .icons import create_icon_canvas, draw_database_glyph
from .labels import make_label

# Width of each fixed column after the stretchy name column. Header and rows
# use the same widths so the columns line up.
FIXED_COLUMNS = (110, 130, 110, 110, 36, 32)
HEADINGS = ("COLLECTIONS", "DOCUMENTS", "DATA SIZE", "STORAGE SIZE", "", "")
SYSTEM_DATABASES = {"admin", "local", "config"}


def configure_columns(frame) -> None:
    """Give a header/row frame the shared column layout.

    Author: Archer
    """
    frame.grid_columnconfigure(0, weight=1)
    for index, width in enumerate(FIXED_COLUMNS, start=1):
        frame.grid_columnconfigure(index, minsize=width)


class DatabaseTable(ctk.CTkFrame):
    """Header row + scrollable list of DatabaseRow."""

    def __init__(self, master, actions) -> None:
        """Author: Archer"""
        super().__init__(master, corner_radius=8, border_width=1,
                         fg_color=get_color("surface/card"),
                         border_color=get_color("border/default"))
        self._actions = actions
        self._rows: list[DatabaseRow] = []
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
        configure_columns(heading)
        make_label(heading, "DATABASE NAME ↓", "column").grid(
            row=0, column=0, sticky="w")
        for index, title in enumerate(HEADINGS, start=1):
            make_label(heading, title, "column").grid(
                row=0, column=index, sticky="w")

    def set_databases(self, databases: list) -> None:
        """Replace all rows with these DatabaseStats.

        Author: Archer
        """
        for row in self._rows:
            row.destroy()
        self._rows = [DatabaseRow(self._body, stats, self._actions)
                      for stats in databases]
        for row in self._rows:
            row.pack(fill="x")

    def apply_filter(self, text: str) -> int:
        """Hide rows whose name doesn't contain `text` (any case).

        Returns how many rows are still shown.

        Author: Archer
        """
        needle = text.strip().lower()
        shown = 0
        for row in self._rows:
            row.pack_forget()
        # Re-pack matches in order so hidden rows don't leave gaps.
        for row in self._rows:
            if needle in row.database.lower():
                row.pack(fill="x")
                shown += 1
        return shown


class DatabaseRow(ctk.CTkFrame):
    """One database: icon, name (+ subtitle), stats, ..., and ›."""

    def __init__(self, master, stats, actions) -> None:
        """Author: Archer"""
        super().__init__(master, corner_radius=0, fg_color="transparent",
                         cursor="hand2")
        self.database = stats.name
        self._actions = actions
        configure_columns(self)
        self._build_name_cell()
        values = (format_count(stats.collections),
                  format_count(stats.documents),
                  format_bytes(stats.data_size),
                  format_bytes(stats.storage_size))
        for index, value in enumerate(values, start=1):
            self._bind_open(make_label(self, value, "body")).grid(
                row=0, column=index, sticky="w")
        self._build_buttons()
        # Thin divider under each row (tk.Frame: a 1px CTkFrame doesn't render).
        tk.Frame(self, height=1, background=get_color("border/default")).grid(
            row=1, column=0, columnspan=len(FIXED_COLUMNS) + 1, sticky="ew")
        self._bind_open(self)

    def _build_name_cell(self) -> None:
        """Database icon, name, and a subtitle for system databases.

        Author: Archer
        """
        cell = ctk.CTkFrame(self, fg_color="transparent")
        cell.grid(row=0, column=0, padx=(16, 0), pady=12, sticky="w")
        icon = create_icon_canvas(cell, 20, get_color("surface/card"))
        draw_database_glyph(icon, get_color("text/secondary"))
        icon.pack(side="left", padx=(0, 12))
        text = ctk.CTkFrame(cell, fg_color="transparent")
        text.pack(side="left")
        self._bind_open(make_label(text, self.database, "body")).pack(
            anchor="w")
        # MongoDB has no database descriptions, so only label system ones.
        if self.database in SYSTEM_DATABASES:
            self._bind_open(make_label(text, "System database", "muted")).pack(
                anchor="w", pady=(2, 0))
        for widget in (cell, icon, text):
            self._bind_open(widget)

    def _build_buttons(self) -> None:
        """The "..." feature menu button and the › open button.

        Author: Archer
        """
        common = {"width": 28, "height": 28, "fg_color": "transparent",
                  "hover_color": get_color("state/hover"),
                  "text_color": get_color("text/secondary"),
                  "font": get_font(14, "bold")}
        self.more_button = ctk.CTkButton(self, text="···",
                                         command=self.show_menu, **common)
        self.more_button.grid(row=0, column=5)
        ctk.CTkButton(self, text="›", command=self.open, **common).grid(
            row=0, column=6)

    def _bind_open(self, widget):
        """Make clicking `widget` open this database; returns the widget.

        Author: Archer
        """
        widget.bind("<Button-1>", lambda _event: self.open())
        return widget

    def open(self) -> None:
        """Go to this database's collections.

        Author: Archer
        """
        self._actions.open_database(self.database)

    def build_menu_items(self) -> list[MenuItem]:
        """Every feature in the "···" menu (Close is added by the menu).

        Only Rename exists so far; add new features here.

        Author: Archer (now MenuItems for the styled FeatureMenu)
        """
        return [MenuItem("Rename", "rename",
                         lambda: self._actions.rename_database(self.database))]

    def show_menu(self) -> FeatureMenu:
        """Pop the styled feature menu up under the "···" button.

        Author: Archer (styled after design/Database features.png)
        """
        return FeatureMenu(self.more_button, self.build_menu_items())
