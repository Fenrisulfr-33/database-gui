"""Left sidebar of the dashboard, styled after design/Dashboard.png.

Author: Archer

Holds the cluster card, the "Databases" nav item, the Explorer (one dropdown
per database that lists its collections), and Disconnect at the bottom.
`actions` is the dashboard's DashboardActions (see views/dashboard_actions.py).
"""

import customtkinter as ctk
from pymongo.errors import PyMongoError

from ..theme import get_color, get_font
from .labels import make_label

SIDEBAR_WIDTH = 236
COLLAPSED = "▸"
EXPANDED = "▾"


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
        """WORKSPACE heading + the (always selected) Databases item.

        Author: Archer
        """
        make_label(self, "WORKSPACE", "section").grid(
            row=1, column=0, padx=16, pady=(0, 8), sticky="w")
        item = ctk.CTkFrame(self, corner_radius=6,
                            fg_color=get_color("state/selected-nav"))
        item.grid(row=2, column=0, padx=16, pady=(0, 20), sticky="ew")
        label = make_label(item, "Databases", "body")
        label.configure(text_color=get_color("state/selected-text"))
        label.pack(side="left", padx=12, pady=8)
        self._count_label = make_label(item, "", "muted")
        self._count_label.pack(side="right", padx=12)

    def _build_explorer(self) -> None:
        """EXPLORER heading with a refresh button, then the database list.

        The dashboard view sets refresh_button's command.

        Author: Archer
        """
        heading = ctk.CTkFrame(self, fg_color="transparent")
        heading.grid(row=3, column=0, padx=16, sticky="ew")
        make_label(heading, "EXPLORER", "section").pack(side="left")
        self.refresh_button = ctk.CTkButton(
            heading, text="↻", width=24, height=24, fg_color="transparent",
            hover_color=get_color("state/hover"), font=get_font(14),
            text_color=get_color("text/secondary"))
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
        for name in names:
            ExplorerItem(self._explorer, name, self._actions).pack(fill="x")


class ExplorerItem(ctk.CTkFrame):
    """One database in the Explorer; click to show/hide its collections."""

    def __init__(self, master, database: str, actions) -> None:
        """Author: Archer"""
        super().__init__(master, fg_color="transparent")
        self._database = database
        self._actions = actions
        self._loaded = False
        self._toggle = ctk.CTkButton(
            self, text=f"{COLLAPSED}  {database}", anchor="w", height=34,
            fg_color="transparent", hover_color=get_color("state/hover"),
            font=get_font(13), text_color=get_color("text/primary"),
            command=self.toggle)
        self._toggle.pack(fill="x")
        self._children_frame = ctk.CTkFrame(self, fg_color="transparent")

    def toggle(self) -> None:
        """Expand (loading collections the first time) or collapse.

        Author: Archer
        """
        if self._children_frame.winfo_manager():
            self._children_frame.pack_forget()
            self._toggle.configure(text=f"{COLLAPSED}  {self._database}")
            return
        if not self._loaded:
            self._load_collections()
        self._children_frame.pack(fill="x")
        self._toggle.configure(text=f"{EXPANDED}  {self._database}")

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
        """A flat button that opens the collection's documents.

        Author: Archer
        """
        ctk.CTkButton(
            self._children_frame, text=collection, anchor="w", height=28,
            fg_color="transparent", hover_color=get_color("state/hover"),
            font=get_font(12), text_color=get_color("text/secondary"),
            command=lambda: self._actions.open_collection(
                self._database, collection),
        ).pack(fill="x", padx=(24, 0))
