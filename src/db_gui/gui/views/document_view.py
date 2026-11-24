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
from ...utils.validators import parse_document_json, parse_documents_json
from ..widgets.dialogs import JsonDocumentDialog
from ..widgets.schema_tab import SchemaActions, SchemaTab


@dataclass
class DocumentActions:
    """The functions the view calls, already set up for one collection."""

    back: Callable[[], None]
    list_documents: Callable[[], list[dict]]
    add_document: Callable[[dict], list[dict]]
    add_documents: Callable[[list[dict]], ImportResult]
    # Author: Archer - None hides the Schema tab
    schema: SchemaActions | None = None


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
            add_buttons, text="Add document", command=self._prompt_add_document
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
        """Clear the list and draw it again."""
        for child in self._document_list.winfo_children():
            child.destroy()
        for document in documents:
            self._add_document_row(document)
        if not documents:
            ctk.CTkLabel(
                self._document_list, text="No documents were found."
            ).pack(pady=20)
        self._update_status(len(documents))

    def _add_document_row(self, document: dict) -> None:
        """Show one document as a grey row."""
        card = ctk.CTkFrame(self._document_list, fg_color=("gray85", "gray20"))
        card.pack(fill="x", pady=4)
        ctk.CTkLabel(
            card,
            text=format_document_preview(document),
            anchor="w",
            font=ctk.CTkFont(family="Courier", size=12),
        ).pack(fill="x", padx=10, pady=8)

    def _update_status(self, count: int) -> None:
        """Show how many documents there are."""
        if count >= DOCUMENT_LIST_LIMIT:
            text = f"Showing the newest {DOCUMENT_LIST_LIMIT} documents."
        else:
            text = f"{count} document{'' if count == 1 else 's'}"
        self._status_label.configure(text=text)

    def _prompt_add_document(self) -> None:
        """Open the dialog for typing a document."""
        JsonDocumentDialog(self, self._submit_document)

    def _submit_document(self, text: str) -> str | None:
        """Add the typed document. Returns an error message or None."""
        try:
            document = parse_document_json(text)
            documents = self._actions.add_document(document)
        except ValueError as error:
            return str(error)
        except PyMongoError:
            return "Could not add the document. Check your permissions."
        self._show_message("")
        self._populate_documents(documents)
        return None

    def _show_message(self, text: str, is_error: bool = False) -> None:
        """Show a red error or green success message."""
        color = "#d9534f" if is_error else "#2e8b57"
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
