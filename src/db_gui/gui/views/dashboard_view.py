"""Dashboard: everything on the connected cluster, styled after
design/Dashboard.png.

Author: Archer

Layout (see expected-behavior.md "Dashboard"):
    header (Docs works, the rest is disabled for now)
    sidebar (Explorer dropdowns) | title, banner, stat cards,
                                 | filter + refresh, database table
    status bar

Stats are loaded on a background thread (one dbStats call per database can
be slow on a big cluster), so the window stays responsive. The thread only
talks to the Tk widgets through a queue that the main thread polls.
"""

import queue
import threading
from datetime import datetime

import customtkinter as ctk
from pymongo.errors import PyMongoError

from ..theme import get_color, get_font
from ..widgets.dashboard_header import DashboardHeader
from ..widgets.dashboard_panels import ConnectionBanner, StatCards, StatusBar
from ..widgets.dashboard_sidebar import DashboardSidebar
from ..widgets.database_table import DatabaseTable
from ..widgets.form_dialog import FormDialog, FormField, FormSpec
from ..widgets.labels import make_button, make_label
from .dashboard_actions import DashboardActions

POLL_MS = 100
# Errors a background load can hit (ValueError = connection already closed).
LOAD_ERRORS = (PyMongoError, ValueError)


class DashboardView(ctk.CTkFrame):
    """The home screen after login."""

    def __init__(self, master, login, actions: DashboardActions) -> None:
        """`login` is the SavedCluster used to sign in (for names only).

        Author: Archer
        """
        super().__init__(master, corner_radius=0,
                         fg_color=get_color("background/app"))
        self._actions = actions
        self._cluster_name = login.name or login.cluster
        self._total_databases = 0
        self.loading = False
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        DashboardHeader(self, login.username).grid(
            row=0, column=0, columnspan=2, sticky="ew")
        self.sidebar = DashboardSidebar(self, self._cluster_name, actions)
        self.sidebar.grid(row=1, column=0, sticky="ns")
        self.sidebar.refresh_button.configure(command=self.refresh)
        self._build_main()
        self.status_bar = StatusBar(self)
        self.status_bar.grid(row=2, column=0, columnspan=2, sticky="ew")
        self.refresh()

    def _build_main(self) -> None:
        """Right-hand content area, top to bottom.

        Author: Archer
        """
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=1, column=1, padx=32, pady=(20, 12), sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(5, weight=1)  # the table stretches
        self._build_title(main)
        self.banner = ConnectionBanner(main, self._cluster_name)
        self.banner.grid(row=1, column=0, pady=(20, 16), sticky="ew")
        self.stat_cards = StatCards(main)
        self.stat_cards.grid(row=2, column=0, pady=(0, 16), sticky="ew")
        self._build_toolbar(main)
        self._error_label = make_label(main, "", "error")
        self.table = DatabaseTable(main, self._actions)
        self.table.grid(row=5, column=0, sticky="nsew")
        self._build_footer(main)

    def _build_title(self, parent) -> None:
        """Breadcrumb, "Databases" title + subtitle, Create database.

        Author: Archer
        """
        top = ctk.CTkFrame(parent, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew")
        make_label(top, f"Connections  /  {self._cluster_name}",
                   "secondary").pack(anchor="w")
        make_label(top, "Databases", "title").pack(anchor="w", pady=(12, 8))
        make_label(top, "Explore and manage the databases on your connection.",
                   "subtitle").pack(anchor="w")
        ctk.CTkButton(
            top, text="+  Create database", height=38, corner_radius=6,
            font=get_font(13, "bold"), fg_color=get_color("button/fill"),
            hover_color=get_color("button/fill-hover"),
            text_color=get_color("button/text"),
            command=self.prompt_create_database,
        ).place(relx=1.0, rely=0.62, anchor="e")

    def _build_toolbar(self, parent) -> None:
        """Filter box, "All databases" (disabled), last-updated, Refresh.

        Author: Archer
        """
        bar = ctk.CTkFrame(parent, fg_color="transparent")
        bar.grid(row=3, column=0, pady=(0, 16), sticky="ew")
        self.filter_entry = ctk.CTkEntry(
            bar, width=320, height=36, corner_radius=6, border_width=1,
            fg_color=get_color("surface/card"),
            border_color=get_color("border/default"),
            text_color=get_color("textbox/text"),
            placeholder_text="⌕  Filter databases by name...",
            placeholder_text_color=get_color("textbox/placeholder"),
            font=get_font(13))
        self.filter_entry.bind("<KeyRelease>", lambda _e: self.apply_filter())
        self.filter_entry.pack(side="left")
        # Placeholder for a future database-type filter.
        make_button(bar, "☰  All databases").pack(side="left", padx=12)
        self._refresh_button = make_button(bar, "↻  Refresh", self.refresh)
        self._refresh_button.pack(side="right")
        self._updated_label = make_label(bar, "", "muted")
        self._updated_label.pack(side="right", padx=14)

    def _build_footer(self, parent) -> None:
        """ "Showing X of Y databases" and the size footnote.

        Author: Archer
        """
        footer = ctk.CTkFrame(parent, fg_color="transparent")
        footer.grid(row=6, column=0, pady=(10, 0), sticky="ew")
        self._showing_label = make_label(footer, "", "muted")
        self._showing_label.pack(side="left")
        make_label(footer, "Sizes include data and indexes · "
                   "Values are estimated", "muted").pack(side="right")

    def refresh(self) -> None:
        """Start reloading stats + status in the background.

        Ignored while a load is already running.

        Author: Archer (now runs on a background thread)
        """
        if self.loading:
            return
        self.loading = True
        self._refresh_button.configure(state="disabled")
        self._updated_label.configure(text="Loading…")
        results: queue.Queue = queue.Queue()
        threading.Thread(target=self._load_in_background, args=(results,),
                         daemon=True).start()
        self.after(POLL_MS, self._poll_load, results)

    def _load_in_background(self, results: queue.Queue) -> None:
        """Runs on the worker thread: talk to MongoDB, never to Tk.

        Author: Archer
        """
        try:
            results.put((self._actions.load_databases(),
                         self._actions.load_status()))
        except LOAD_ERRORS:
            results.put(None)

    def _poll_load(self, results: queue.Queue) -> None:
        """Runs on the Tk thread: check whether the worker has finished.

        Author: Archer
        """
        if not self.winfo_exists():
            return  # user left the dashboard; drop the result
        try:
            outcome = results.get_nowait()
        except queue.Empty:
            self.after(POLL_MS, self._poll_load, results)
            return
        self.loading = False
        self._refresh_button.configure(state="normal")
        if outcome is None:
            self._updated_label.configure(text="")
            self.show_error("Could not reach the cluster. Try Refresh again.")
            return
        self._show_overview(*outcome)

    def _show_overview(self, databases: list, status) -> None:
        """Redraw every part of the dashboard from freshly loaded data.

        Author: Archer
        """
        self.clear_error()
        self._total_databases = len(databases)
        self.sidebar.set_databases([db.name for db in databases])
        self.sidebar.set_host(status.host)
        self.banner.set_status(status)
        self.status_bar.set_status(status)
        self.stat_cards.set_databases(databases)
        self.table.set_databases(databases)
        self.apply_filter()
        self._updated_label.configure(
            text=f"Updated {datetime.now():%H:%M:%S}")

    def apply_filter(self) -> None:
        """Hide table rows that don't match the filter box.

        Author: Archer
        """
        shown = self.table.apply_filter(self.filter_entry.get())
        self._showing_label.configure(
            text=f"Showing {shown} of {self._total_databases} databases")

    def show_error(self, message: str) -> None:
        """Show an error line between the toolbar and the table.

        Author: Archer
        """
        self._error_label.configure(text=message)
        self._error_label.grid(row=4, column=0, pady=(0, 10), sticky="w")

    def clear_error(self) -> None:
        """Author: Archer"""
        self._error_label.grid_forget()

    def prompt_create_database(self) -> FormDialog:
        """Open the Create database pop-up (design/Create database — pop-up).

        MongoDB only keeps a database that has a collection, so the pop-up
        also asks for the first collection's name.

        Author: Archer (styled pop-up replaces the two input dialogs)
        """
        spec = FormSpec(
            title="Create database",
            subtitle=f"Create a new database in {self._cluster_name}.",
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
