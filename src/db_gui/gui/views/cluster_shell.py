"""Persistent frame around the pages of a connected cluster.

Author: Archer

The header, sidebar (Explorer), and status bar are built ONCE per login and
stay on screen while you move between the Dashboard, Collections, Documents,
and Add document pages. Only the main area (the current ClusterPage) is
swapped out. Before this, every click / insert / create destroyed and rebuilt
the whole window, which flickered and threw away the sidebar's state (which
databases were expanded, their loaded collections).

    +---------------- header ----------------+
    | sidebar |  content  <- show_page() swaps |
    |         |             only this part     |
    +-------------- status bar --------------+
"""

import customtkinter as ctk

from ..theme import get_color
from ..widgets.dashboard_header import DashboardHeader
from ..widgets.dashboard_panels import StatusBar
from ..widgets.dashboard_sidebar import DashboardSidebar
from .dashboard_actions import DashboardActions


class ClusterShell(ctk.CTkFrame):
    """Header + sidebar + status bar that outlive the page shown inside."""

    def __init__(self, master, login, actions: DashboardActions) -> None:
        """`login` is the SavedCluster used to sign in (for names only).

        Author: Archer
        """
        super().__init__(master, corner_radius=0,
                         fg_color=get_color("background/app"))
        self.actions = actions
        self.cluster_name = login.name or login.cluster
        self.page = None  # the ClusterPage currently in self.content
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.header = DashboardHeader(self, login.username)
        self.header.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.sidebar = DashboardSidebar(self, self.cluster_name, actions)
        self.sidebar.grid(row=1, column=0, sticky="ns")
        self.sidebar.refresh_button.configure(command=self.refresh_explorer)
        # Pages are gridded into this frame by show_page().
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.grid(row=1, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)
        self.status_bar = StatusBar(self)
        self.status_bar.grid(row=2, column=0, columnspan=2, sticky="ew")

    def show_page(self, make_page):
        """Replace only the main area with `make_page(self)`; returns the page.

        `make_page` is a page class or any function taking the shell, e.g.
        `lambda shell: CollectionsView(shell, "shop")`.

        Author: Archer
        """
        if self.page is not None:
            self.page.destroy()
        self.page = make_page(self)
        self.page.grid(row=0, column=0, sticky="nsew")
        # Move the green highlight right away, before the page's data loads.
        self.sidebar.select_database(self.page.selected_database)
        return self.page

    def show_cluster_data(self, names: list[str], status) -> None:
        """Update the shared parts after a page load. The sidebar only adds
        or removes databases that changed, so this is cheap.

        Author: Archer
        """
        self.sidebar.set_databases(names)
        self.sidebar.set_host(status.host)
        self.status_bar.set_status(status)

    def refresh_explorer(self) -> None:
        """Explorer's refresh button: re-read every database's collections,
        then reload the current page (which also refreshes the db list).

        Author: Archer
        """
        self.sidebar.reload_all_collections()
        if self.page is not None:
            self.page.refresh()
