"""Base class for the pages inside a connected cluster (Dashboard,
Collections, Documents, Add document).

Author: Archer (the header, sidebar, and status bar moved to ClusterShell,
which stays on screen; a page is now just the main area, so switching pages
or reloading one no longer rebuilds the whole window)

A page is created inside a ClusterShell (see cluster_shell.py) and fills its
`self.main` area. It also owns background loading: `refresh()` runs the page's `load_page()` on a
worker thread (MongoDB calls can be slow), then hands the result to
`show_page()` on the Tk thread via a queue the Tk thread polls.

Subclasses implement:
    _build_main()          fill self.main (called once)
    load_page()            WORKER THREAD: return (database_names, page_data)
    show_page(page_data)   Tk thread: draw page_data
and may set self.selected_database to highlight one in the sidebar.
"""

import queue
import threading

import customtkinter as ctk
from pymongo.errors import PyMongoError

from ..assets import SEARCH, make_icon_label
from ..theme import get_color, get_font
from ..widgets.labels import make_label

POLL_MS = 100
# Errors a background load can hit (ValueError = connection already closed).
LOAD_ERRORS = (PyMongoError, ValueError)


class ClusterPage(ctk.CTkFrame):
    """The page-specific main area shown inside a ClusterShell."""

    selected_database: str | None = None

    def __init__(self, shell) -> None:
        """`shell` is the ClusterShell this page is shown in.

        Author: Archer (built inside the shell's content area instead of
        drawing its own header / sidebar / status bar)
        """
        super().__init__(shell.content, corner_radius=0,
                         fg_color="transparent")
        self.shell = shell
        self._actions = shell.actions
        self.cluster_name = shell.cluster_name
        self.sidebar = shell.sidebar  # shared; lives as long as the shell
        self.loading = False
        self._refresh_button = None  # pages with a Refresh button set this
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.main = ctk.CTkFrame(self, fg_color="transparent")
        self.main.grid(row=0, column=0, padx=32, pady=(20, 12), sticky="nsew")
        self.main.grid_columnconfigure(0, weight=1)
        self._error_label = make_label(self.main, "", "error")
        self._build_main()
        self.refresh()

    # ----- helpers pages use to build their main area -----

    def make_filter(self, parent, placeholder: str) -> ctk.CTkFrame:
        """Search-icon filter box that calls self.apply_filter() as you type.

        Returns the bordered box (caller packs it); the entry inside is
        self.filter_entry. The border lives on the box, not the entry, so the
        icon sits inside it and typed text never runs under the icon.

        Author: Archer (search.png icon instead of the ⌕ character)
        """
        card = get_color("surface/card")
        box = ctk.CTkFrame(parent, width=320, height=36, corner_radius=6,
                           border_width=1, fg_color=card,
                           border_color=get_color("border/default"))
        box.pack_propagate(False)  # keep the 320x36 size
        make_icon_label(box, SEARCH, card).pack(side="left", padx=(12, 0))
        self.filter_entry = ctk.CTkEntry(
            box, height=30, border_width=0, fg_color=card,
            text_color=get_color("textbox/text"),
            placeholder_text=placeholder,
            placeholder_text_color=get_color("textbox/placeholder"),
            font=get_font(13))
        self.filter_entry.pack(side="left", fill="x", expand=True, padx=(2, 6))
        self.filter_entry.bind("<KeyRelease>",
                               lambda _event: self.apply_filter())
        return box

    def make_primary_button(self, parent, text: str, command):
        """Green "+ Create ..." button.

        Author: Archer
        """
        return ctk.CTkButton(
            parent, text=text, height=38, corner_radius=6,
            font=get_font(13, "bold"), fg_color=get_color("button/fill"),
            hover_color=get_color("button/fill-hover"),
            text_color=get_color("button/text"), command=command)

    def show_error(self, message: str) -> None:
        """Error line just above the table (grid row 4 of self.main).

        Author: Archer
        """
        self._error_label.configure(text=message)
        self._error_label.grid(row=4, column=0, pady=(0, 10), sticky="w")

    def clear_error(self) -> None:
        """Author: Archer"""
        self._error_label.grid_forget()

    # ----- background loading -----

    def refresh(self) -> None:
        """Start reloading this page's data in the background (ignored if
        already loading). Only this page's widgets are redrawn afterwards.

        Author: Archer
        """
        if self.loading:
            return
        self.loading = True
        if self._refresh_button is not None:
            self._refresh_button.configure(state="disabled")
        self.on_load_started()
        results: queue.Queue = queue.Queue()
        threading.Thread(target=self._load_in_background, args=(results,),
                         daemon=True).start()
        self.after(POLL_MS, self._poll_load, results)

    def _load_in_background(self, results: queue.Queue) -> None:
        """WORKER THREAD: talk to MongoDB, never to Tk.

        Author: Archer
        """
        try:
            names, page_data = self.load_page()
            results.put((names, self._actions.load_status(), page_data))
        except LOAD_ERRORS:
            results.put(None)

    def _poll_load(self, results: queue.Queue) -> None:
        """Tk thread: check whether the worker has finished.

        Author: Archer
        """
        if not self.winfo_exists():
            return  # user left this page; drop the result
        try:
            outcome = results.get_nowait()
        except queue.Empty:
            self.after(POLL_MS, self._poll_load, results)
            return
        self.loading = False
        if self._refresh_button is not None:
            self._refresh_button.configure(state="normal")
        if outcome is None:
            self.show_error("Could not reach the cluster. Try Refresh again.")
            self.on_load_failed()
            return
        self._show_loaded(*outcome)

    def _show_loaded(self, names: list, status, page_data) -> None:
        """Update the shell's shared parts, then let the page draw its own.

        Author: Archer (the shell updates the sidebar in place)
        """
        self.clear_error()
        self.shell.show_cluster_data(names, status)
        self.show_page(page_data, status)

    # ----- hooks for subclasses -----

    def _build_main(self) -> None:
        raise NotImplementedError

    def load_page(self):
        raise NotImplementedError

    def show_page(self, page_data, status) -> None:
        raise NotImplementedError

    def apply_filter(self) -> None:
        """Pages with a filter box override this."""

    def on_load_started(self) -> None:
        """Optional hook, e.g. show "Loading…"."""

    def on_load_failed(self) -> None:
        """Optional hook, e.g. clear "Loading…"."""
