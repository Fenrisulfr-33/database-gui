"""Screen for one collection: shows its documents and adds new ones.

Author: Archer (Documents / Schema tabs)
"""

from collections.abc import Callable
from dataclasses import dataclass

from tkinter import filedialog

import customtkinter as ctk

from ...db.connection import DOCUMENT_LIST_LIMIT, ImportResult, PyMongoError
from ...utils.files import read_text_file
from ...utils.formatters import format_document_preview
from ...utils.validators import parse_documents_json
from ..widgets.schema_tab import SchemaActions, SchemaTab

# Author: Archer - rows for documents that break the collection's schema
BROKEN_LABEL = "⚠  Doesn't match schema"
BROKEN_ROW_COLORS = ("#f6d5d3", "#3a2224")  # (light, dark)
ERROR_COLOR = "#d9534f"


@dataclass
class DocumentActions:
    """The functions the view calls, already set up for one collection."""

    back: Callable[[], None]
    list_documents: Callable[[], list[dict]]
    # Author: Archer - opens the Add document page (was a pop-up)
    open_add_document: Callable[[], None]
    add_documents: Callable[[list[dict]], ImportResult]
    # Author: Archer - None hides the Schema tab
    schema: SchemaActions | None = None
    # Author: Archer - (ids) -> set of ids that break the schema
    find_mismatches: Callable[[list], set] | None = None


class DocumentView(ctk.CTkFrame):
    """Shows the documents in a collection."""

    def __init__(
        self, master: ctk.CTk, title: str, actions: DocumentActions
    ) -> None:
        super().__init__(master)
        self._title = title
        self._actions = actions
        self._build_view()
        self._load_documents()

    def _build_view(self) -> None:
        """Title, Back, and the Documents / Schema tabs.

        Author: Archer (moved the document list into a Documents tab)
        """
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            self, text=self._title, font=ctk.CTkFont(size=24, weight="bold"),
        ).grid(row=0, column=0, padx=30, pady=(30, 8), sticky="w")
        ctk.CTkButton(
            self, text="Back", command=self._actions.back, width=120
        ).grid(row=0, column=1, padx=30, pady=(30, 8), sticky="e")
        self.tabs = ctk.CTkTabview(self)
        self.tabs.grid(row=1, column=0, columnspan=2, padx=30, pady=(0, 20),
                       sticky="nsew")
        self._build_documents_tab(self.tabs.add("Documents"))
        if self._actions.schema is not None:
            self.schema_tab = SchemaTab(self.tabs.add("Schema"),
                                        self._actions.schema)
            self.schema_tab.pack(fill="both", expand=True)
            # Saving or removing the schema changes which rows are marked.
            self.schema_tab.on_change = self._load_documents

    def _build_documents_tab(self, tab: ctk.CTkFrame) -> None:
        """Status line, document list and buttons.

        Author: Archer (now inside the Documents tab)
        """
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)
        self._status_label = ctk.CTkLabel(tab, text="")
        self._status_label.grid(row=0, column=0, padx=10, pady=(4, 8),
                                sticky="w")
        self._document_list = ctk.CTkScrollableFrame(tab, height=300)
        self._document_list.grid(row=1, column=0, padx=10, pady=6,
                                 sticky="nsew")
        self._build_buttons(tab)

    def _build_buttons(self, tab: ctk.CTkFrame) -> None:
        """Add document and Import JSON file, then the message line."""
        add_buttons = ctk.CTkFrame(tab, fg_color="transparent")
        add_buttons.grid(row=2, column=0, padx=10, pady=10, sticky="w")
        ctk.CTkButton(
            add_buttons, text="Add document",
            command=self._actions.open_add_document
        ).pack(side="left", padx=(0, 10))
        ctk.CTkButton(
            add_buttons, text="Import JSON file", command=self._import_file
        ).pack(side="left")
        self._message_label = ctk.CTkLabel(tab, text="")
        self._message_label.grid(row=3, column=0, padx=10, sticky="w")

    def _load_documents(self) -> None:
        """Get the documents when the screen opens."""
        try:
            documents = self._actions.list_documents()
        except (ValueError, PyMongoError):
            self._show_message("Could not load documents.", is_error=True)
            documents = []
        self._populate_documents(documents)

    def _populate_documents(self, documents: list[dict]) -> None:
        """Clear the list and draw it again.

        Author: Archer (marks documents that break the schema)
        """
        for child in self._document_list.winfo_children():
            child.destroy()
        broken = self._find_broken(documents)
        for document in documents:
            self._add_document_row(document, document.get("_id") in broken)
        if not documents:
            ctk.CTkLabel(
                self._document_list, text="No documents were found."
            ).pack(pady=20)
        self._update_status(len(documents), len(broken))

    def _find_broken(self, documents: list[dict]) -> set:
        """Ids of the shown documents that don't match the schema.

        If the check fails, nothing is marked (the list still shows).

        Author: Archer
        """
        if self._actions.find_mismatches is None or not documents:
            return set()
        ids = [document["_id"] for document in documents if "_id" in document]
        try:
            return self._actions.find_mismatches(ids)
        except (ValueError, PyMongoError):
            return set()

    def _add_document_row(self, document: dict, broken: bool = False) -> None:
        """Show one document as a grey row, red-tinted if it breaks the schema.

        Author: Archer (added the "Doesn't match schema" marker)
        """
        card = ctk.CTkFrame(
            self._document_list,
            fg_color=BROKEN_ROW_COLORS if broken else ("gray85", "gray20"))
        card.pack(fill="x", pady=4)
        if broken:
            ctk.CTkLabel(card, text=BROKEN_LABEL, text_color=ERROR_COLOR,
                         font=ctk.CTkFont(size=12, weight="bold")).pack(
                side="right", padx=10)
        ctk.CTkLabel(
            card,
            text=format_document_preview(document),
            anchor="w",
            font=ctk.CTkFont(family="Courier", size=12),
        ).pack(fill="x", padx=10, pady=8)

    def _update_status(self, count: int, broken: int = 0) -> None:
        """Show how many documents there are, and how many break the schema.

        Author: Archer (added the schema count)
        """
        if count >= DOCUMENT_LIST_LIMIT:
            text = f"Showing the newest {DOCUMENT_LIST_LIMIT} documents."
        else:
            text = f"{count} document{'' if count == 1 else 's'}"
        if broken:
            text += f" · {broken} {'doesn' if broken == 1 else 'don'}'t match the schema"
        self._status_label.configure(text=text)

    def _show_message(self, text: str, is_error: bool = False) -> None:
        """Show a red error or green success message."""
        color = ERROR_COLOR if is_error else "#2e8b57"
        self._message_label.configure(text=text, text_color=color)

    def _choose_file(self) -> str:
        """Open the file picker. Returns "" if cancelled."""
        return filedialog.askopenfilename(
            title="Import JSON file",
            filetypes=[("JSON files", "*.json *.jsonl"), ("All files", "*.*")],
        )

    def _import_file(self) -> None:
        """Add every document from a chosen file."""
        path = self._choose_file()
        if not path:
            return
        try:
            documents = parse_documents_json(read_text_file(path))
            result = self._actions.add_documents(documents)
        except ValueError as error:
            self._show_message(str(error), is_error=True)
            return
        except PyMongoError:
            self._show_message(
                "Could not import the file. Check your permissions.",
                is_error=True,
            )
            return
        self._populate_documents(result.documents)
        self._show_message(self._describe_import(result))

    @staticmethod
    def _describe_import(result: ImportResult) -> str:
        """Message with how many were added or skipped."""
        noun = "document" if result.inserted == 1 else "documents"
        text = f"Imported {result.inserted} {noun}."
        if result.skipped:
            text += f" {result.skipped} skipped (for example, a duplicate _id)."
        return text
