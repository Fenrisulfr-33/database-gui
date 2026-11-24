"""Left sidebar of the dashboard, styled after design/Dashboard.png.

Author: Archer

Holds the cluster card, the "Databases" nav item (back to the dashboard), the
Explorer (one dropdown per database that lists its collections), and
Disconnect at the bottom. Shared by the Dashboard and Collections pages.

Author note: clicking a database's NAME opens its Collections page; the
chevron only shows/hides its collections. The open database is highlighted
green and expanded (see select_database).
`actions` is the dashboard's DashboardActions (see views/dashboard_actions.py).
Author note: chevrons, refresh, and the collection table icon are now the
design PNGs (see gui/assets.py) instead of text glyphs / canvas drawings.
"""

import customtkinter as ctk
from pymongo.errors import PyMongoError

from ..assets import (CHEVRON_DOWN, CHEVRON_RIGHT, REFRESH, TABLE,
                      load_image, make_icon_label, set_icon)
from ..theme import get_color, get_font
from .labels import make_label

SIDEBAR_WIDTH = 236
COLLAPSED = CHEVRON_RIGHT  # icon file shown on a closed database
EXPANDED = CHEVRON_DOWN  # icon file shown on an open database


class DashboardSidebar(ctk.CTkFrame):
    """Cluster card, nav, Explorer dropdowns, and Disconnect."""

    def __init__(self, master, cluster_name: str, actions) -> None:
        """Author: Archer"""
        super().__init__(master, width=SIDEBAR_WIDTH, corner_radius=0,
                         fg_color=get_color("surface/chrome"))
        self.grid_propagate(False)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)  # Explorer list takes spare room
        self._actions = actions
        self._build_cluster_card(cluster_name)
        self._build_nav()
        self._build_explorer()
        self._build_footer()

    def _build_cluster_card(self, cluster_name: str) -> None:
        """Card with a green dot, the cluster name, and its host below.

        Author: Archer
        """
        card = ctk.CTkFrame(self, corner_radius=8, border_width=1,
                            fg_color="transparent",
                            border_color=get_color("border/default"))
        card.grid(row=0, column=0, padx=16, pady=(16, 20), sticky="ew")
        title_row = ctk.CTkFrame(card, fg_color="transparent")
        title_row.pack(anchor="w", padx=12, pady=(12, 4))
        dot = make_label(title_row, "●", "body")
        dot.configure(text_color=get_color("accent/primary"))
        dot.pack(side="left", padx=(0, 8))
        make_label(title_row, cluster_name, "body-bold").pack(side="left")
        self._host_label = make_label(card, "", "muted")
        self._host_label.pack(anchor="w", padx=12, pady=(0, 12))

    def _build_nav(self) -> None:
        """WORKSPACE heading + the Databases item (click: dashboard).

        Author: Archer (now clickable)
        """
        make_label(self, "WORKSPACE", "section").grid(
            row=1, column=0, padx=16, pady=(0, 8), sticky="w")
        item = ctk.CTkFrame(self, corner_radius=6, cursor="hand2",
                            fg_color=get_color("state/selected-nav"))
        item.grid(row=2, column=0, padx=16, pady=(0, 20), sticky="ew")
        label = make_label(item, "Databases", "body")
        label.configure(text_color=get_color("state/selected-text"))
        label.pack(side="left", padx=12, pady=8)
        self._count_label = make_label(item, "", "muted")
        self._count_label.pack(side="right", padx=12)
        for widget in (item, label, self._count_label):
            widget.bind("<Button-1>", lambda _event: self._actions.go_home())

    def _build_explorer(self) -> None:
        """EXPLORER heading with a refresh button, then the database list.

        The dashboard view sets refresh_button's command.

        Author: Archer (refresh now uses the refresh-cw icon)
        """
        heading = ctk.CTkFrame(self, fg_color="transparent")
        heading.grid(row=3, column=0, padx=16, sticky="ew")
        make_label(heading, "EXPLORER", "section").pack(side="left")
        self.refresh_button = ctk.CTkButton(
            heading, text="", width=24, height=24, fg_color="transparent",
            hover_color=get_color("state/hover"))
        set_icon(self.refresh_button, REFRESH)
        self.refresh_button.pack(side="right")
        self._explorer = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0)
        self._explorer.grid(row=4, column=0, padx=(8, 4), pady=(4, 0),
                            sticky="nsew")

    def _build_footer(self) -> None:
        """Disconnect at the bottom (returns to the login screen).

        Author: Archer
        """
        ctk.CTkButton(
            self, text="⎋  Disconnect", anchor="w", height=36,
            fg_color="transparent", hover_color=get_color("state/hover"),
            font=get_font(13), text_color=get_color("text/primary"),
            command=self._actions.disconnect,
        ).grid(row=5, column=0, padx=8, pady=16, sticky="ew")

    def set_host(self, host: str) -> None:
        """Show the cluster host under the name on the card.

        Author: Archer
        """
        self._host_label.configure(text=host)

    def set_databases(self, names: list[str]) -> None:
        """Rebuild the Explorer with one collapsed dropdown per database.

        Author: Archer
        """
        self._count_label.configure(text=str(len(names)))
        for child in self._explorer.winfo_children():
            child.destroy()
        self.items = {}
        for name in names:
            self.items[name] = ExplorerItem(self._explorer, name, self._actions)
            self.items[name].pack(fill="x")

    def select_database(self, name: str) -> None:
        """Highlight `name` green and expand it (the open database).

        Author: Archer
        """
        item = self.items.get(name)
        if item is not None:
            item.set_selected()


class ExplorerItem(ctk.CTkFrame):
    """One database in the Explorer: chevron shows/hides its collections,
    the name opens its Collections page."""

    def __init__(self, master, database: str, actions) -> None:
        """Author: Archer (split into chevron + name button; chevron icons)"""
        super().__init__(master, fg_color="transparent")
        self._database = database
        self._actions = actions
        self._loaded = False
        self.header = ctk.CTkFrame(self, corner_radius=6,
                                   fg_color="transparent")
        self.header.pack(fill="x")
        common = {"height": 34, "fg_color": "transparent",
                  "hover_color": get_color("state/hover"), "font": get_font(13),
                  "text_color": get_color("text/primary")}
        # Both chevron images are loaded once and swapped on toggle.
        self._chevron_images = {name: load_image(name, self)
                                for name in (COLLAPSED, EXPANDED)}
        self._chevron = ctk.CTkButton(self.header, text="", width=24,
                                      command=self.toggle, **common)
        self._set_chevron(COLLAPSED)
        self._chevron.pack(side="left")
        self.name_button = ctk.CTkButton(
            self.header, text=database, anchor="w",
            command=lambda: actions.open_database(database), **common)
        self.name_button.pack(side="left", fill="x", expand=True)
        self._children_frame = ctk.CTkFrame(self, fg_color="transparent")

    def set_selected(self) -> None:
        """Green highlight (design/Collections.png) and expand.

        Author: Archer
        """
        green = get_color("state/selected-nav")
        self.header.configure(fg_color=green)
        for button in (self._chevron, self.name_button):
            button.configure(fg_color=green, hover_color=green,
                             text_color=get_color("state/selected-text"))
        if not self.is_expanded():
            self.toggle()

    def _set_chevron(self, icon_name: str) -> None:
        """Show COLLAPSED (right) or EXPANDED (down) on the chevron button.

        Author: Archer
        """
        self.chevron_icon = icon_name  # remembered so tests can check it
        self._chevron.configure(image=self._chevron_images[icon_name])

    def is_expanded(self) -> bool:
        """Author: Archer"""
        return bool(self._children_frame.winfo_manager())

    def toggle(self) -> None:
        """Expand (loading collections the first time) or collapse.

        Author: Archer (swaps chevron icons instead of text)
        """
        if self.is_expanded():
            self._children_frame.pack_forget()
            self._set_chevron(COLLAPSED)
            return
        if not self._loaded:
            self._load_collections()
        self._children_frame.pack(fill="x")
        self._set_chevron(EXPANDED)

    def _load_collections(self) -> None:
        """Ask the cluster for this database's collections, once.

        Author: Archer
        """
        try:
            collections = self._actions.list_collections(self._database)
        except PyMongoError:
            make_label(self._children_frame, "Couldn't load collections",
                       "error").pack(anchor="w", padx=32, pady=4)
            return
        self._loaded = True
        if not collections:
            make_label(self._children_frame, "No collections", "muted").pack(
                anchor="w", padx=32, pady=4)
        for collection in collections:
            self._add_collection(collection)

    def _add_collection(self, collection: str) -> None:
        """Table icon + flat button that opens the collection's documents.

        Author: Archer (table icon is now the design's table-2 PNG)
        """
        row = ctk.CTkFrame(self._children_frame, fg_color="transparent")
        row.pack(fill="x", padx=(28, 0))
        icon = make_icon_label(row, TABLE, get_color("surface/chrome"))
        icon.pack(side="left", padx=(0, 4))
        ctk.CTkButton(
            row, text=collection, anchor="w", height=28,
            fg_color="transparent", hover_color=get_color("state/hover"),
            font=get_font(12), text_color=get_color("text/secondary"),
            command=lambda: self._actions.open_collection(
                self._database, collection),
        ).pack(side="left", fill="x", expand=True)
