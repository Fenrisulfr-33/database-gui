"""Add document page, styled after design/Add document.png.

Author: Archer (replaces the old Add document pop-up)

Same frame as the Dashboard (header, sidebar, status bar from ClusterPage).
Main area, top to bottom:
- breadcrumb: <cluster> / <database> / <collection> / Add document
- title + subtitle, and "← Back to documents"
- green banner: which cluster the document goes to
- JSON editor card (left) + Document details panel (right)
- footer: ready/not ready line, Cancel, "+ Insert document"

The design's "Validate before insert" checkbox is replaced by a Schema info
line: schemas are strict, so validation can't be switched off (see
expected-behavior.md > Documents Page > Add document page).
"""

import tkinter as tk
import webbrowser
from collections.abc import Callable
from dataclasses import dataclass

import customtkinter as ctk
from pymongo.errors import PyMongoError

from ...db.schema import UnsupportedSchemaError
from ..assets import TABLE, make_icon_label
from ..theme import get_color, get_font
from ..widgets.json_editor import JsonEditor
from ..widgets.labels import make_button, make_label
from .cluster_page import ClusterPage

EXTENDED_JSON_URL = (
    "https://www.mongodb.com/docs/manual/reference/mongodb-extended-json/")
DETAILS_WIDTH = 280
SCHEMA_TEXTS = {
    None: "Checking…",
    True: "Enforced. Documents that don't match the collection's schema "
          "are rejected.",
    False: "None. This collection accepts any document.",
}


@dataclass
class AddDocumentPage:
    """Which collection the page adds to, and the db/ calls it needs.

    Author: Archer
    """

    database: str
    collection: str
    # (document) -> list[dict]: inserts it (raises ValueError when rejected)
    add_document: Callable[[dict], list]
    # () -> dict | None: the collection's schema (WORKER THREAD)
    get_schema: Callable[[], dict | None]


class AddDocumentView(ClusterPage):
    """Type a document as JSON and insert it.

    Author: Archer
    """

    def __init__(self, master, login, page) -> None:
        """`page` is (actions, AddDocumentPage).

        Author: Archer
        """
        actions, self.page = page
        self.selected_database = self.page.database
        super().__init__(master, login, actions)
        # On the text box itself, so it runs before Tk types a newline.
        self.editor.text.bind("<Control-Return>", self._on_shortcut)

    def _build_main(self) -> None:
        """Main area, top to bottom.

        Author: Archer
        """
        self.main.grid_rowconfigure(3, weight=1)  # editor row stretches
        self._build_title()
        self._build_banner()
        self._build_content()
        self._build_footer()

    def _build_title(self) -> None:
        """Breadcrumb, title, subtitle, and Back to documents.

        Author: Archer
        """
        top = ctk.CTkFrame(self.main, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew")
        self._build_breadcrumb(top)
        make_label(top, "Add document", "title").pack(anchor="w", pady=(12, 8))
        make_label(top, f"Create a new document in {self._namespace()}.",
                   "subtitle").pack(anchor="w")
        back = make_button(top, "←  Back to documents", self.go_back)
        back.place(relx=1.0, rely=0.62, anchor="e")

    def _build_breadcrumb(self, parent) -> None:
        """<cluster> / <database> / <collection> / Add document.

        Each part but the last is a link.

        Author: Archer
        """
        crumbs = ctk.CTkFrame(parent, fg_color="transparent")
        crumbs.pack(anchor="w")
        links = (
            (self.cluster_name, self._actions.go_home),
            (self.page.database,
             lambda: self._actions.open_database(self.page.database)),
            (self.page.collection, self.go_back),
        )
        for text, command in links:
            link = make_label(crumbs, text, "secondary")
            link.configure(cursor="hand2")
            link.bind("<Button-1>", lambda _event, run=command: run())
            link.pack(side="left")
            make_label(crumbs, "  /  ", "secondary").pack(side="left")
        make_label(crumbs, "Add document", "secondary").pack(side="left")

    def _build_banner(self) -> None:
        """Green notice: which cluster the document goes to.

        Author: Archer
        """
        banner = ctk.CTkFrame(self.main, corner_radius=6, border_width=1,
                              fg_color=get_color("accent/surface"),
                              border_color=get_color("accent/border"))
        banner.grid(row=1, column=0, pady=(20, 20), sticky="ew")
        text = (f"ⓘ  You are connected to {self.cluster_name}. This document "
                "will be inserted when you select Insert document.")
        label = make_label(banner, text, "body")
        label.configure(text_color=get_color("accent/primary"))
        label.pack(anchor="w", padx=16, pady=12)

    def _build_content(self) -> None:
        """JSON editor on the left, Document details on the right.

        Author: Archer
        """
        content = ctk.CTkFrame(self.main, fg_color="transparent")
        content.grid(row=3, column=0, sticky="nsew")
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(0, weight=1)
        self.editor = JsonEditor(content, self._on_editor_change)
        self.editor.grid(row=0, column=0, padx=(0, 20), sticky="nsew")
        self._build_details(content)

    def _build_details(self, parent) -> None:
        """Document details panel.

        Author: Archer
        """
        panel = ctk.CTkFrame(parent, width=DETAILS_WIDTH, corner_radius=8,
                             border_width=1, fg_color=get_color("surface/card"),
                             border_color=get_color("border/default"))
        panel.grid(row=0, column=1, sticky="ns")
        panel.pack_propagate(False)  # keep the fixed width
        body = ctk.CTkFrame(panel, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=20)
        make_label(body, "Document details", "body-bold").pack(anchor="w")
        self._build_destination(body)
        tk.Frame(body, height=1, background=get_color("border/default")).pack(
            fill="x", pady=16)
        self._add_note(body, "Document ID", "Provide an _id or leave it out "
                       "to generate an ObjectId automatically.")
        self._add_note(body, "BSON data types", "Use Extended JSON for "
                       "ObjectId, Date, Decimal128, and other BSON types.")
        self.schema_label = self._add_note(body, "Schema", SCHEMA_TEXTS[None])
        link = make_label(body, "Extended JSON reference ↗", "link")
        link.configure(font=get_font(12), cursor="hand2")
        link.bind("<Button-1>",
                  lambda _event: webbrowser.open(EXTENDED_JSON_URL))
        link.pack(anchor="w", pady=(4, 0))

    def _build_destination(self, parent) -> None:
        """DESTINATION, database name, and the collection with its icon.

        Author: Archer
        """
        make_label(parent, "DESTINATION", "section").pack(anchor="w",
                                                          pady=(20, 8))
        make_label(parent, self.page.database, "secondary").pack(anchor="w")
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(anchor="w", pady=(6, 0))
        make_icon_label(row, TABLE, get_color("surface/card")).pack(
            side="left", padx=(0, 8))
        make_label(row, self.page.collection, "link").pack(side="left")

    @staticmethod
    def _add_note(parent, heading: str, text: str) -> ctk.CTkLabel:
        """Bold heading + wrapped grey text. Returns the text label.

        Author: Archer
        """
        make_label(parent, heading, "body-bold").pack(anchor="w")
        label = make_label(parent, text, "secondary")
        label.configure(wraplength=DETAILS_WIDTH - 40, justify="left")
        label.pack(anchor="w", pady=(6, 16))
        return label

    def _build_footer(self) -> None:
        """Ready line on the left; shortcut hint, Cancel, Insert on the right.

        Author: Archer
        """
        footer = ctk.CTkFrame(self.main, fg_color="transparent")
        footer.grid(row=4, column=0, pady=(20, 0), sticky="ew")
        self.ready_label = make_label(footer, "", "secondary")
        self.ready_label.pack(side="left")
        self.insert_button = self.make_primary_button(
            footer, "+  Insert document", self.insert_document)
        self.insert_button.pack(side="right")
        make_button(footer, "Cancel", self.go_back).pack(side="right",
                                                         padx=10)
        make_label(footer, "Ctrl ↵", "muted").pack(side="right", padx=6)
        self._on_editor_change(not self.editor.error)

    # ----- behavior -----

    def _on_editor_change(self, is_valid: bool) -> None:
        """Enable Insert only for a valid document.

        Called by the editor while it's being built, before the footer
        exists, so it checks first.

        Author: Archer
        """
        if not hasattr(self, "insert_button"):
            return
        self.insert_button.configure(
            state="normal" if is_valid else "disabled")
        self.set_ready_text(
            "🛡  1 document ready to insert · Changes are not yet saved"
            if is_valid else "Fix the JSON above before inserting.")

    def set_ready_text(self, text: str, is_error: bool = False) -> None:
        """Author: Archer"""
        self.ready_label.configure(text=text, text_color=get_color(
            "feedback/danger" if is_error else "text/secondary"))

    def insert_document(self) -> None:
        """Insert the typed document, then go back to the documents list.

        Errors (bad JSON, duplicate _id, schema rejection) stay on the page.

        Author: Archer
        """
        try:
            self.page.add_document(self.editor.get_document())
        except ValueError as error:
            self.set_ready_text(str(error), is_error=True)
            return
        except PyMongoError:
            self.set_ready_text(
                "Could not insert the document. Check your permissions.",
                is_error=True)
            return
        self.go_back()

    def _on_shortcut(self, _event=None) -> str:
        """Ctrl+Enter inserts (if the document is valid).

        Author: Archer
        """
        if not self.editor.error:
            self.insert_document()
        return "break"

    def go_back(self) -> None:
        """Back to this collection's documents.

        Author: Archer
        """
        self._actions.open_collection(self.page.database, self.page.collection)

    def _namespace(self) -> str:
        """Author: Archer"""
        return f"{self.page.database}.{self.page.collection}"

    # ----- ClusterPage hooks -----

    def load_page(self):
        """WORKER THREAD: database names (sidebar) + whether there's a schema.

        A validator this app can't show still counts as a schema.

        Author: Archer
        """
        names = self._actions.list_database_names()
        try:
            has_schema = self.page.get_schema() is not None
        except UnsupportedSchemaError:
            has_schema = True
        return names, has_schema

    def show_page(self, page_data, status) -> None:
        """Author: Archer"""
        self.schema_label.configure(text=SCHEMA_TEXTS[page_data])
