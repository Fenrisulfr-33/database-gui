"""Collections page for one database, styled after design/Collections.png.

Author: Archer (replaces the old plain collection_view.py)

Same frame as the Dashboard (header, sidebar, status bar from ClusterPage),
with this database highlighted green + expanded in the sidebar. Main area:
breadcrumb (back to the dashboard), title, Create collection, tabs
(Collections / Statistics - disabled for now), stat cards, filter + Name A-Z
sort + Refresh, and the collection table. Each row's "···" menu has
Rename collection; clicking a row opens its documents.

Author note (Archer): built inside the persistent ClusterShell; create /
rename now reload just this page and this database's sidebar collections.
"""

import tkinter as tk

import customtkinter as ctk
from pymongo.errors import PyMongoError

from ..assets import REFRESH, TABLE, set_icon
from ..theme import get_color, get_font
from ..widgets.dashboard_panels import StatCards, collection_card_texts
from ..widgets.feature_menu import MenuItem
from ..widgets.form_dialog import FormDialog, FormField, FormSpec
from ..widgets.labels import make_button, make_label
from ..widgets.stats_table import SYSTEM_DATABASES, StatsTable, TableConfig
from ...utils.formatters import format_bytes, format_count
from .cluster_page import ClusterPage

CARD_TITLES = ("Documents", "Data size", "Storage size", "Indexes")
SORT_LABELS = {False: "⇅  Name: A–Z", True: "⇅  Name: Z–A"}


class CollectionsView(ClusterPage):
    """Every collection in one database, with stats."""

    def __init__(self, shell, database: str) -> None:
        """`shell` is the ClusterShell; `database` is the one to show.

        Author: Archer (takes the shell instead of master/login/actions)
        """
        self.database = database
        self.selected_database = self.database  # green in the sidebar
        self._collections: list = []
        self._descending = False
        super().__init__(shell)

    def _build_main(self) -> None:
        """Main area, top to bottom.

        Author: Archer
        """
        self.main.grid_rowconfigure(5, weight=1)  # the table stretches
        self._build_title()
        self._build_tabs()
        self.stat_cards = StatCards(self.main, CARD_TITLES)
        self.stat_cards.grid(row=2, column=0, pady=(0, 16), sticky="ew")
        self._build_toolbar()
        self.table = StatsTable(self.main, self._table_config())
        self.table.grid(row=5, column=0, sticky="nsew")
        self._build_footer()

    def _table_config(self) -> TableConfig:
        """Columns + behavior for the collection table.

        Author: Archer
        """
        return TableConfig(
            name_heading="COLLECTION NAME ↓",
            headings=("DOCUMENTS", "DATA SIZE", "INDEXES", "INDEX SIZE",
                      "FIELDS"),
            widths=(110, 100, 80, 100, 70),
            icon=TABLE,  # table-2 PNG from the design
            values=lambda c: (format_count(c.documents),
                              format_bytes(c.data_size),
                              format_count(c.indexes),
                              format_bytes(c.index_size),
                              format_count(c.fields)),
            on_open=lambda c: self._actions.open_collection(
                self.database, c.name),
            menu_items=lambda c: [MenuItem(
                "Rename", "rename",
                lambda: self.prompt_rename_collection(c.name))],
        )

    def _build_title(self) -> None:
        """Clickable breadcrumb, database name, subtitle, Create collection.

        Author: Archer
        """
        top = ctk.CTkFrame(self.main, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew")
        crumbs = ctk.CTkFrame(top, fg_color="transparent")
        crumbs.pack(anchor="w")
        for text in (self.cluster_name, "Databases"):
            link = make_label(crumbs, text, "secondary")
            link.configure(cursor="hand2")
            link.bind("<Button-1>", lambda _event: self._actions.go_home())
            link.pack(side="left")
            make_label(crumbs, "  /  ", "secondary").pack(side="left")
        make_label(crumbs, self.database, "secondary").pack(side="left")
        make_label(top, self.database, "title").pack(anchor="w", pady=(12, 8))
        subtitle = ("System database" if self.database in SYSTEM_DATABASES
                    else "Explore and manage the collections in this database.")
        make_label(top, subtitle, "subtitle").pack(anchor="w")
        self.make_primary_button(top, "+  Create collection",
                                 self.prompt_create_collection).place(
            relx=1.0, rely=0.62, anchor="e")

    def _build_tabs(self) -> None:
        """"Collections N" (active, green underline) and "Statistics"
        (disabled until it's built).

        Author: Archer
        """
        tabs = ctk.CTkFrame(self.main, fg_color="transparent")
        tabs.grid(row=1, column=0, pady=(20, 16), sticky="ew")
        row = ctk.CTkFrame(tabs, fg_color="transparent")
        row.pack(fill="x")
        active = ctk.CTkFrame(row, fg_color="transparent")
        active.pack(side="left")
        self._tab_label = make_label(active, "Collections", "body-bold")
        self._tab_label.configure(text_color=get_color("accent/primary"))
        self._tab_label.pack(pady=(0, 8))
        # Green underline under the active tab (tk.Frame: thin CTkFrames
        # don't render).
        tk.Frame(active, height=2,
                 background=get_color("accent/primary")).pack(fill="x")
        statistics = make_button(row, "Statistics")
        statistics.configure(fg_color="transparent", border_width=0,
                             font=get_font(13), height=24,
                             text_color_disabled=get_color("text/secondary"))
        statistics.pack(side="left", padx=(20, 0), anchor="n")
        # Thin grey line under both tabs.
        tk.Frame(tabs, height=1,
                 background=get_color("border/default")).pack(fill="x")

    def _build_toolbar(self) -> None:
        """Filter box, Name A–Z / Z–A sort, Refresh.

        Author: Archer (refresh-cw icon from the design)
        """
        bar = ctk.CTkFrame(self.main, fg_color="transparent")
        bar.grid(row=3, column=0, pady=(0, 16), sticky="ew")
        self.make_filter(bar, "Filter collections by name...").pack(
            side="left")
        self._refresh_button = make_button(bar, "Refresh", self.refresh)
        set_icon(self._refresh_button, REFRESH)
        self._refresh_button.pack(side="right")
        self.sort_button = make_button(bar, SORT_LABELS[False],
                                       self.toggle_sort)
        self.sort_button.pack(side="right", padx=12)

    def _build_footer(self) -> None:
        """ "Showing X of Y collections" and the hint on the right.

        Author: Archer
        """
        footer = ctk.CTkFrame(self.main, fg_color="transparent")
        footer.grid(row=6, column=0, pady=(10, 0), sticky="ew")
        self._showing_label = make_label(footer, "", "muted")
        self._showing_label.pack(side="left")
        make_label(footer, "ⓘ  Select a collection to explore its documents",
                   "muted").pack(side="right")

    # ----- ClusterPage hooks -----

    def load_page(self):
        """WORKER THREAD: sidebar names, database totals, collection stats.

        Author: Archer
        """
        names = self._actions.list_database_names()
        database = self._actions.load_database_stats(self.database)
        collections = self._actions.load_collection_stats(self.database)
        return names, (database, collections)

    def show_page(self, page_data, status) -> None:
        """Redraw cards, tab count, and table.

        Author: Archer
        """
        database, self._collections = page_data
        count = len(self._collections)
        self._tab_label.configure(text=f"Collections  {count}")
        self.stat_cards.set_values(collection_card_texts(database, count))
        self._draw_table()

    def _draw_table(self) -> None:
        """Fill the table in the current sort order, keeping the filter.

        Author: Archer
        """
        ordered = sorted(self._collections, key=lambda c: c.name.lower(),
                         reverse=self._descending)
        self.table.set_items(ordered)
        self.apply_filter()

    def toggle_sort(self) -> None:
        """Flip between Name A–Z and Z–A.

        Author: Archer
        """
        self._descending = not self._descending
        self.sort_button.configure(text=SORT_LABELS[self._descending])
        self._draw_table()

    def apply_filter(self) -> None:
        """Hide rows that don't match the filter box.

        Author: Archer
        """
        shown = self.table.apply_filter(self.filter_entry.get())
        self._showing_label.configure(
            text=f"Showing {shown} of {len(self._collections)} collections")

    # ----- Create / rename collection -----

    def prompt_create_collection(self) -> FormDialog:
        """Create collection pop-up (same style as Create database).

        Author: Archer
        """
        spec = FormSpec(
            title="Create collection",
            subtitle=f"Create a new collection in {self.database}.",
            submit_text="Create",
            fields=[FormField("Collection name", "e.g. customers",
                              "Use a unique name in this database.")])
        return FormDialog(self, spec, self._create_collection)

    def _create_collection(self, values: list[str]) -> str | None:
        """Pop-up submit: create, refresh, or return the error to show.

        Author: Archer
        """
        try:
            self._actions.create_collection(self.database, values[0])
        except ValueError as error:
            return str(error)
        except PyMongoError:
            return "Could not create collection. Check its name and permissions."
        self._reload_after_change()
        return None

    def prompt_rename_collection(self, name: str) -> FormDialog:
        """Rename collection pop-up with the current name filled in.

        Author: Archer
        """
        spec = FormSpec(
            title="Rename collection",
            subtitle=f"Enter a new name for '{name}'.",
            submit_text="Rename",
            fields=[FormField("New collection name", "",
                              "Choose a unique name in this database.",
                              initial=name)])
        return FormDialog(self, spec,
                          lambda values: self._rename_collection(name, values))

    def _rename_collection(self, name: str, values: list[str]) -> str | None:
        """Pop-up submit: rename, refresh, or return the error to show.

        Author: Archer
        """
        new_name = values[0]
        if new_name == name:
            return "Choose a different name."
        try:
            self._actions.rename_collection(self.database, name, new_name)
        except ValueError as error:
            return str(error)
        except PyMongoError:
            return "Could not rename collection. Check your permissions."
        self._reload_after_change()
        return None

    def _reload_after_change(self) -> None:
        """After create / rename: reload this page's table and this
        database's sidebar collections (nothing else is redrawn).

        Author: Archer
        """
        self.sidebar.reload_collections(self.database)
        self.refresh()
