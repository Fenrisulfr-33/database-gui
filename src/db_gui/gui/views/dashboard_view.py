"""Dashboard: everything on the connected cluster, styled after
design/Dashboard.png.

Author: Archer (now built on ClusterPage, shared with the Collections page)

Layout (see expected-behavior.md "Dashboard"):
    header / sidebar / status bar  (from ClusterPage)
    main: title, connection banner, stat cards, filter + refresh, table
"""

from datetime import datetime

import customtkinter as ctk
from pymongo.errors import PyMongoError

from ..assets import REFRESH, SLIDERS, set_icon
from ..widgets.dashboard_panels import (ConnectionBanner, StatCards,
                                        database_card_texts)
from ..widgets.feature_menu import MenuItem
from ..widgets.form_dialog import FormDialog, FormField, FormSpec
from ..widgets.icons import draw_database_glyph
from ..widgets.labels import make_button, make_label
from ..widgets.stats_table import SYSTEM_DATABASES, StatsTable, TableConfig
from ...utils.formatters import format_bytes, format_count
from .cluster_page import ClusterPage

CARD_TITLES = ("Databases", "Collections", "Documents", "Storage size")


class DashboardView(ClusterPage):
    """The home screen after login."""

    def _build_main(self) -> None:
        """Main area, top to bottom.

        Author: Archer
        """
        self._total_databases = 0
        self.main.grid_rowconfigure(5, weight=1)  # the table stretches
        self._build_title()
        self.banner = ConnectionBanner(self.main, self.cluster_name)
        self.banner.grid(row=1, column=0, pady=(20, 16), sticky="ew")
        self.stat_cards = StatCards(self.main, CARD_TITLES)
        self.stat_cards.grid(row=2, column=0, pady=(0, 16), sticky="ew")
        self._build_toolbar()
        self.table = StatsTable(self.main, self._table_config())
        self.table.grid(row=5, column=0, sticky="nsew")
        self._build_footer()

    def _table_config(self) -> TableConfig:
        """Columns + behavior for the database table.

        Author: Archer
        """
        return TableConfig(
            name_heading="DATABASE NAME ↓",
            headings=("COLLECTIONS", "DOCUMENTS", "DATA SIZE", "STORAGE SIZE"),
            widths=(110, 130, 110, 110),
            icon=draw_database_glyph,
            values=lambda db: (format_count(db.collections),
                               format_count(db.documents),
                               format_bytes(db.data_size),
                               format_bytes(db.storage_size)),
            on_open=lambda db: self._actions.open_database(db.name),
            menu_items=lambda db: [MenuItem(
                "Rename", "rename",
                lambda: self._actions.rename_database(db.name))],
            # MongoDB has no database descriptions; only label system ones.
            subtitle=lambda db: ("System database"
                                 if db.name in SYSTEM_DATABASES else ""),
        )

    def _build_title(self) -> None:
        """Breadcrumb, "Databases" title + subtitle, Create database.

        Author: Archer
        """
        top = ctk.CTkFrame(self.main, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew")
        make_label(top, f"Connections  /  {self.cluster_name}",
                   "secondary").pack(anchor="w")
        make_label(top, "Databases", "title").pack(anchor="w", pady=(12, 8))
        make_label(top, "Explore and manage the databases on your connection.",
                   "subtitle").pack(anchor="w")
        self.make_primary_button(top, "+  Create database",
                                 self.prompt_create_database).place(
            relx=1.0, rely=0.62, anchor="e")

    def _build_toolbar(self) -> None:
        """Filter box, "All databases" (disabled), last-updated, Refresh.

        Author: Archer (sliders / refresh-cw icons from the design)
        """
        bar = ctk.CTkFrame(self.main, fg_color="transparent")
        bar.grid(row=3, column=0, pady=(0, 16), sticky="ew")
        self.make_filter(bar, "Filter databases by name...").pack(side="left")
        # Placeholder for a future database-type filter.
        all_button = make_button(bar, "All databases")
        set_icon(all_button, SLIDERS)
        all_button.pack(side="left", padx=12)
        self._refresh_button = make_button(bar, "Refresh", self.refresh)
        set_icon(self._refresh_button, REFRESH)
        self._refresh_button.pack(side="right")
        self._updated_label = make_label(bar, "", "muted")
        self._updated_label.pack(side="right", padx=14)

    def _build_footer(self) -> None:
        """ "Showing X of Y databases" and the size footnote.

        Author: Archer
        """
        footer = ctk.CTkFrame(self.main, fg_color="transparent")
        footer.grid(row=6, column=0, pady=(10, 0), sticky="ew")
        self._showing_label = make_label(footer, "", "muted")
        self._showing_label.pack(side="left")
        make_label(footer, "Sizes include data and indexes · "
                   "Values are estimated", "muted").pack(side="right")

    # ----- ClusterPage hooks -----

    def load_page(self):
        """WORKER THREAD: stats for every database.

        Author: Archer
        """
        databases = self._actions.load_databases()
        return [db.name for db in databases], databases

    def show_page(self, databases: list, status) -> None:
        """Redraw banner, cards, and table from fresh stats.

        Author: Archer
        """
        self._total_databases = len(databases)
        self.banner.set_status(status)
        self.stat_cards.set_values(database_card_texts(databases))
        self.table.set_items(databases)
        self.apply_filter()
        self._updated_label.configure(
            text=f"Updated {datetime.now():%H:%M:%S}")

    def on_load_started(self) -> None:
        """Author: Archer"""
        self._updated_label.configure(text="Loading…")

    def on_load_failed(self) -> None:
        """Author: Archer"""
        self._updated_label.configure(text="")

    def apply_filter(self) -> None:
        """Hide table rows that don't match the filter box.

        Author: Archer
        """
        shown = self.table.apply_filter(self.filter_entry.get())
        self._showing_label.configure(
            text=f"Showing {shown} of {self._total_databases} databases")

    # ----- Create database -----

    def prompt_create_database(self) -> FormDialog:
        """Open the Create database pop-up (design/Create database — pop-up).

        MongoDB only keeps a database that has a collection, so the pop-up
        also asks for the first collection's name.

        Author: Archer
        """
        spec = FormSpec(
            title="Create database",
            subtitle=f"Create a new database in {self.cluster_name}.",
            submit_text="Create",
            fields=[
                FormField("Database name", "e.g. customer_data",
                          "Use a unique name for this connection."),
                FormField("First collection name", "e.g. customers",
                          "A database needs at least one collection."),
            ])
        return FormDialog(self, spec, self._create_database)

    def _create_database(self, values: list[str]) -> str | None:
        """Pop-up submit: create it, refresh, or return the error to show.

        Author: Archer
        """
        database, collection = values
        try:
            self._actions.create_database(database, collection)
        except ValueError as error:
            return str(error)
        except PyMongoError:
            return "Could not create database. Check its name and your permissions."
        self.refresh()
        return None
