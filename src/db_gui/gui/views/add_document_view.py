"""Add document page, styled after design/Add document.png.

Author: Archer (replaces the old Add document pop-up)

Same frame as the Dashboard (header, sidebar, status bar from ClusterPage).
Main area, top to bottom:
- breadcrumb: <cluster> / <database> / <collection> / Add document
- title + subtitle, and "← Back to documents"
- green banner: which cluster the document goes to
- JSON editor card (left) + Document details panel (right)
- footer: ready/not ready line, Cancel, "+ Insert document"

When the collection has a schema the simplified view can show, the JSON
editor is swapped for a form built from it (widgets/schema_form.py) once the
background load finds the schema. Unsupported schemas keep the JSON editor;
MongoDB still checks what gets inserted.

The design's "Validate before insert" checkbox is replaced by a Schema info
line: schemas are strict, so validation can't be switched off (see
expected-behavior.md > Documents Page > Add document page).

Author note (Archer): built inside the persistent ClusterShell, so opening
this page and going back after an insert only redraws the main area.

Author note (Archer): the same page is the **Edit document** page when
AddDocumentPage.original is set (the "✎ Edit" button on a document card).
It starts filled in with that document (JSON editor, or the schema form),
the _id can't be changed, and "Save changes" replaces the stored document.
Texts that differ between the two live in MODE_TEXTS.
"""

import tkinter as tk
import webbrowser
from collections.abc import Callable
from dataclasses import dataclass

import customtkinter as ctk
from pymongo.errors import PyMongoError

from ...db.schema import UnsupportedSchemaError, parse_schema
from ...utils.formatters import format_document_pretty
from ..assets import TABLE, make_icon_label
from ..theme import get_color, get_font
from ..widgets.json_editor import JsonEditor
from ..widgets.labels import make_button, make_label
from ..widgets.schema_form import SchemaForm
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
JSON_TYPES_TEXT = ("Use Extended JSON for ObjectId, Date, Decimal128, and "
                   "other BSON types.")
FORM_TYPES_TEXT = ("Each field is converted to its schema type. Dates use "
                   "YYYY-MM-DD. Empty optional fields are saved as null.")
# Texts that differ between adding (False) and editing (True) a document.
MODE_TEXTS = {
    False: {
        "title": "Add document",
        "subtitle": "Create a new document in {namespace}.",
        "banner": "inserted when you select Insert document",
        "button": "+  Insert document",
        "ready": "🛡  1 document ready to insert · Changes are not yet saved",
        "form_ready": "Fill in the fields, then select Insert document.",
        "id_note": "Provide an _id or leave it out to generate an ObjectId "
                   "automatically.",
    },
    True: {
        "title": "Edit document",
        "subtitle": "Change this document in {namespace}.",
        "banner": "updated when you select Save changes",
        "button": "✓  Save changes",
        "ready": "🛡  Ready to save · Changes are not yet saved",
        "form_ready": "Change the fields, then select Save changes.",
        "id_note": "The _id can't be changed. It says which document is "
                   "updated.",
    },
}


@dataclass
class AddDocumentPage:
    """Which collection the page adds to, and the db/ calls it needs.

    Author: Archer
    """

    database: str
    collection: str
    # (document) -> saves it: inserts on Add, replaces on Edit (raises
    # ValueError when rejected)
    save_document: Callable[[dict], object]
    # () -> dict | None: the collection's schema (WORKER THREAD)
    get_schema: Callable[[], dict | None]
    # The stored document being edited; None = adding a new one.
    original: dict | None = None


class AddDocumentView(ClusterPage):
    """Type a document (JSON, or a form when there's a schema) and insert it.

    Author: Archer
    """

    form: SchemaForm | None = None  # set once a usable schema is found

    def __init__(self, shell, page: AddDocumentPage) -> None:
        """`shell` is the ClusterShell; `page` says which collection.

        Author: Archer (takes the shell instead of master/login/actions;
        picks the Add or Edit texts)
        """
        self.page = page
        self.editing = page.original is not None
        self.texts = MODE_TEXTS[self.editing]
        self.selected_database = self.page.database
        super().__init__(shell)
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
        make_label(top, self.texts["title"], "title").pack(anchor="w",
                                                           pady=(12, 8))
        subtitle = self.texts["subtitle"].format(namespace=self._namespace())
        make_label(top, subtitle, "subtitle").pack(anchor="w")
        back = make_button(top, "←  Back to documents", self.go_back)
        back.place(relx=1.0, rely=0.62, anchor="e")

    def _build_breadcrumb(self, parent) -> None:
        """<cluster> / <database> / <collection> / Add (or Edit) document.

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
        make_label(crumbs, self.texts["title"], "secondary").pack(side="left")

    def _build_banner(self) -> None:
        """Green notice: which cluster the document goes to.

        Author: Archer
        """
        banner = ctk.CTkFrame(self.main, corner_radius=6, border_width=1,
                              fg_color=get_color("accent/surface"),
                              border_color=get_color("accent/border"))
        banner.grid(row=1, column=0, pady=(20, 20), sticky="ew")
        text = (f"ⓘ  You are connected to {self.cluster_name}. This document "
                f"will be {self.texts['banner']}.")
        label = make_label(banner, text, "body")
        label.configure(text_color=get_color("accent/primary"))
        label.pack(anchor="w", padx=16, pady=12)

    def _build_content(self) -> None:
        """JSON editor on the left, Document details on the right.

        Author: Archer
        """
        self.content = ctk.CTkFrame(self.main, fg_color="transparent")
        self.content.grid(row=3, column=0, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)
        self.editor = JsonEditor(self.content, self._on_editor_change)
        self.editor.grid(row=0, column=0, padx=(0, 20), sticky="nsew")
        if self.editing:  # start with the stored document
            self.editor.set_text(format_document_pretty(self.page.original))
        self._build_details(self.content)

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
        self._add_note(body, "Document ID", self.texts["id_note"])
        self.types_label = self._add_note(body, "BSON data types",
                                          JSON_TYPES_TEXT)
        self.schema_label = self._add_note(body, "Schema", SCHEMA_TEXTS[None])
        self.json_link = make_label(body, "Extended JSON reference ↗", "link")
        self.json_link.configure(font=get_font(12), cursor="hand2")
        self.json_link.bind("<Button-1>",
                            lambda _event: webbrowser.open(EXTENDED_JSON_URL))
        self.json_link.pack(anchor="w", pady=(4, 0))

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
            footer, self.texts["button"], self.insert_document)
        self.insert_button.pack(side="right")
        make_button(footer, "Cancel", self.go_back).pack(side="right",
                                                         padx=10)
        make_label(footer, "Ctrl ↵", "muted").pack(side="right", padx=6)
        self._on_editor_change(not self.editor.error)

    # ----- behavior -----

    def _on_editor_change(self, is_valid: bool) -> None:
        """Enable Insert only for a valid document.

        Called by the editor while it's being built, before the footer
        exists, so it checks first. Ignored once the form replaced it.

        Author: Archer
        """
        if not hasattr(self, "insert_button") or self.form is not None:
            return
        self.insert_button.configure(
            state="normal" if is_valid else "disabled")
        self.set_ready_text(self.texts["ready"] if is_valid
                            else "Fix the JSON above before saving.")

    def set_ready_text(self, text: str, is_error: bool = False) -> None:
        """Author: Archer"""
        self.ready_label.configure(text=text, text_color=get_color(
            "feedback/danger" if is_error else "text/secondary"))

    def insert_document(self) -> None:
        """Save the typed document (insert, or replace on Edit), then go
        back to the documents list.

        Errors (bad JSON, fields marked red, duplicate _id, changed _id,
        schema rejection) stay on the page.

        Author: Archer (reads from the form when there is one; also saves
        edits)
        """
        try:
            self.page.save_document(self._read_document())
        except ValueError as error:
            self.set_ready_text(str(error), is_error=True)
            return
        except PyMongoError:
            self.set_ready_text(
                "Could not insert the document. Check your permissions.",
                is_error=True)
            return
        self.go_back()

    def _read_document(self) -> dict:
        """The typed document; on Edit, with the stored _id kept.

        Raises ValueError (bad input, or the _id was changed).

        Author: Archer
        """
        document = (self.form or self.editor).get_document()
        if not self.editing:
            return document
        original_id = self.page.original["_id"]
        if "_id" in document and document["_id"] != original_id:
            raise ValueError("The _id can't be changed. Use Add document to "
                             "make a new document instead.")
        # _id first, like MongoDB stores it (and if it was deleted).
        rest = {key: value for key, value in document.items() if key != "_id"}
        return {"_id": original_id, **rest}

    def _on_shortcut(self, _event=None) -> str:
        """Ctrl+Enter inserts (if the JSON is valid; the form checks itself).

        Author: Archer
        """
        if self.form is not None or not self.editor.error:
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
        """WORKER THREAD: database names (sidebar), plus (has_schema, fields).

        fields is None when there's no schema, or one the form can't show
        (that still counts as a schema).

        Author: Archer
        """
        names = self._actions.list_database_names()
        try:
            schema = self.page.get_schema()
            fields = None if schema is None else parse_schema(schema)
        except UnsupportedSchemaError:
            return names, (True, None)
        return names, (schema is not None, fields)

    def show_page(self, page_data, status) -> None:
        """Schema line, and swap in the form the first time it's possible.

        Author: Archer
        """
        has_schema, fields = page_data
        self.schema_label.configure(text=SCHEMA_TEXTS[has_schema])
        if fields and self.form is None:
            self.use_form(fields)

    def use_form(self, fields: list) -> None:
        """Replace the JSON editor with a form built from the schema.

        Author: Archer
        """
        self.editor.grid_remove()
        self.form = SchemaForm(self.content, fields, self._on_shortcut)
        self.form.grid(row=0, column=0, padx=(0, 20), sticky="nsew")
        self.types_label.configure(text=FORM_TYPES_TEXT)
        self.json_link.pack_forget()  # the form doesn't use Extended JSON
        self.insert_button.configure(state="normal")
        self.set_ready_text(self.texts["form_ready"])
        if self.editing:
            self._fill_form()

    def _fill_form(self) -> None:
        """Edit page: put the stored values in the form (bad ones turn red)
        and warn about fields the schema doesn't have.

        Author: Archer
        """
        extra = self.form.fill(self.page.original)
        if extra:
            self.set_ready_text(
                "⚠  Not in the schema, removed when saved: " + ", ".join(extra),
                is_error=True)
