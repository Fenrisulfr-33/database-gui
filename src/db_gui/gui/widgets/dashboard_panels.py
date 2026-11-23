"""Smaller dashboard pieces: connection banner, stat cards, status bar.

Author: Archer

Each piece is built empty and filled in by a set_* method, so the dashboard
can call those again on Refresh without rebuilding the widgets.
"""

from importlib import metadata

import customtkinter as ctk

from ...utils.formatters import format_bytes, format_compact_count, format_count
from ..theme import get_color
from .database_table import SYSTEM_DATABASES
from .icons import create_icon_canvas, draw_database_glyph
from .labels import make_button, make_label


def _total(values: list) -> int | None:
    """Sum the known values; None if the server reported none of them.

    Author: Archer
    """
    known = [value for value in values if value is not None]
    return sum(known) if known else None


def _app_version() -> str:
    """The installed package version, for the status bar.

    Author: Archer
    """
    try:
        return metadata.version("database-gui")
    except metadata.PackageNotFoundError:
        return "dev"


class ConnectionBanner(ctk.CTkFrame):
    """Strip under the title: icon, cluster name, health badge, host."""

    def __init__(self, master, cluster_name: str) -> None:
        """Author: Archer"""
        super().__init__(master, corner_radius=8, border_width=1,
                         fg_color=get_color("surface/card"),
                         border_color=get_color("border/default"))
        icon = create_icon_canvas(self, 20, get_color("surface/card"))
        draw_database_glyph(icon, get_color("accent/primary"))
        icon.pack(side="left", padx=(18, 14), pady=14)
        make_label(self, cluster_name, "body-bold").pack(side="left")
        self._badge = make_label(self, "", "muted")
        self._badge.configure(corner_radius=4)
        self._badge.pack(side="left", padx=16, ipadx=8, ipady=2)
        self._host = make_label(self, "", "secondary")
        self._host.pack(side="left")
        # Placeholder for a future connection-details screen.
        view = make_button(self, "View connection ↗")
        view.configure(fg_color="transparent", border_width=0)
        view.pack(side="right", padx=12)

    def set_status(self, status) -> None:
        """Show the host and "● Healthy" (ping worked) or "● Unreachable".

        Author: Archer
        """
        self._host.configure(text=status.host)
        if status.ping_ms is None:
            self._badge.configure(
                text="● Unreachable", text_color=get_color("feedback/danger"),
                fg_color=get_color("feedback/danger-subtle"))
        else:
            self._badge.configure(
                text="● Healthy", text_color=get_color("accent/primary"),
                fg_color=get_color("accent/badge"))


class StatCards(ctk.CTkFrame):
    """Four totals across the cluster: databases, collections, documents,
    storage size."""

    TITLES = ("Databases", "Collections", "Documents", "Storage size")

    def __init__(self, master) -> None:
        """Author: Archer"""
        super().__init__(master, fg_color="transparent")
        self._cards = [self._build_card(index, title)
                       for index, title in enumerate(self.TITLES)]

    def _build_card(self, column: int, title: str) -> tuple:
        """One card: title, big value, small note. Returns (value, note).

        Author: Archer
        """
        self.grid_columnconfigure(column, weight=1, uniform="stat")
        card = ctk.CTkFrame(self, corner_radius=8, border_width=1,
                            fg_color=get_color("surface/card"),
                            border_color=get_color("border/default"))
        card.grid(row=0, column=column, padx=(0 if column == 0 else 16, 0),
                  sticky="nsew")
        make_label(card, title, "secondary").pack(anchor="w", padx=14,
                                                  pady=(14, 8))
        value = make_label(card, "", "stat")
        value.pack(anchor="w", padx=14)
        note = make_label(card, "", "muted")
        note.pack(anchor="w", padx=14, pady=(8, 14))
        return value, note

    def set_databases(self, databases: list) -> None:
        """Recompute every card from a list of DatabaseStats.

        Author: Archer
        """
        system = sum(1 for db in databases if db.name in SYSTEM_DATABASES)
        documents = _total([db.documents for db in databases])
        data = _total([db.data_size for db in databases])
        texts = (
            (str(len(databases)),
             f"{len(databases) - system} application · {system} system"),
            (format_count(_total([db.collections for db in databases])),
             "Across all databases"),
            (format_compact_count(documents),
             f"{format_count(documents)} total documents"),
            (format_bytes(_total([db.storage_size for db in databases])),
             f"{format_bytes(data)} logical data size"),
        )
        for (value, note), (value_text, note_text) in zip(self._cards, texts):
            value.configure(text=value_text)
            note.configure(text=note_text)


class StatusBar(ctk.CTkFrame):
    """Bottom strip: connection + ping, MongoDB version, app version."""

    def __init__(self, master) -> None:
        """Author: Archer"""
        super().__init__(master, height=26, corner_radius=0,
                         fg_color=get_color("surface/chrome"))
        self._left = make_label(self, "", "muted")
        self._left.pack(side="left", padx=16, pady=4)
        make_label(self, f"Arrow_> v{_app_version()}", "muted").pack(
            side="right", padx=16)

    def set_status(self, status) -> None:
        """e.g. "● Connected · 24 ms    MongoDB 7.0.14 · Replica set rs0".

        Author: Archer
        """
        if status.ping_ms is None:
            self._left.configure(text="● Not responding",
                                 text_color=get_color("feedback/danger"))
            return
        parts = [f"● Connected · {status.ping_ms} ms"]
        if status.version:
            parts.append(f"MongoDB {status.version}")
        if status.replica_set:
            parts.append(f"Replica set {status.replica_set}")
        self._left.configure(text="    ".join(parts),
                             text_color=get_color("text/muted"))
