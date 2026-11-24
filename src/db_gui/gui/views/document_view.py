"""Documents page for one collection, styled like design/Collections.png.

Author: Archer (restyled onto the shared cluster frame; there's no Figma
mockup for this page, so it follows the Collections page)

Same frame as the Dashboard (header, sidebar, status bar from ClusterPage),
with the collection's database highlighted in the sidebar. Main area:
- breadcrumb: <cluster> / Databases / <database> / <collection>
- title + subtitle, Import JSON file, and "+ Add document"
- tabs: "Documents N" and "Schema" (green underline on the active one)
- Documents tab: filter + Refresh, the document cards (indented JSON +
  Edit button), "Showing X of Y"
- Schema tab: widgets/schema_tab.py

Documents load on a background thread like the other cluster pages. Rows
for documents that break the collection's schema are tinted red and say
"Doesn't match schema".

Author note (Archer): built inside the persistent ClusterShell, so opening
this page or importing only redraws the main area.
Author note (Archer): each document is a card showing the whole document as
indented JSON colored like the JSON editor (keys normal text, values green),
with an "✎ Edit" button that opens the Edit document page.
"""

import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass
from tkinter import filedialog

import customtkinter as ctk

from ...db.connection import DOCUMENT_LIST_LIMIT, ImportResult, PyMongoError
from ...utils.files import read_text_file
from ...utils.formatters import format_document_pretty
from ...utils.validators import parse_documents_json
from ..assets import REFRESH, set_icon
from ..theme import get_color, get_font
from ..widgets.json_editor import TOKEN_PATTERN
from ..widgets.labels import make_button, make_label
from ..widgets.schema_tab import SchemaActions, SchemaTab
from .cluster_page import ClusterPage

DOCUMENTS_TAB = "Documents"
SCHEMA_TAB = "Schema"
BROKEN_LABEL = "⚠  Doesn't match schema"
# Preview token colors (token names come from the JSON editor's
# TOKEN_PATTERN): keys in normal text and every value green, as in
# design/Add document.png. Anything else (brackets, commas) stays grey.
PREVIEW_COLORS = {"key": "text/primary", "string": "accent/primary",
                  "literal": "accent/primary"}


@dataclass
class DocumentPage:
    """Which collection the page shows, and the db/ calls it needs.

    Author: Archer (was DocumentActions)
    """

    database: str
    collection: str
    # () -> list[dict]: newest documents (WORKER THREAD)
    list_documents: Callable[[], list[dict]]
    # (documents) -> ImportResult
    add_documents: Callable[[list[dict]], ImportResult]
    # () -> None: opens the Add document page
    open_add_document: Callable[[], None]
    # None hides the Schema tab
    schema: SchemaActions | None = None
    # (ids) -> set of ids that break the schema (WORKER THREAD)
    find_mismatches: Callable[[list], set] | None = None
    # (document) -> None: opens the Edit document page; None hides Edit
    open_edit_document: Callable[[dict], None] | None = None


class DocumentView(ClusterPage):
    """The documents in one collection, plus its Schema tab.

    Author: Archer
    """

    def __init__(self, shell, page: DocumentPage) -> None:
        """`shell` is the ClusterShell; `page` says which collection.

        Author: Archer (takes the shell instead of master/login/actions)
        """
        self.page = page
        self.selected_database = self.page.database
        self._documents: list[dict] = []
        self._broken: set = set()
        self.rows: list[DocumentRow] = []
        self.tabs: dict[str, tuple] = {}
        super().__init__(shell)

    def _build_main(self) -> None:
        """Main area, top to bottom.

        Author: Archer
        """
        self.main.grid_rowconfigure(5, weight=1)  # the active tab stretches
        self._build_title()
        self._build_tabs()
        self.documents_panel = self._build_documents_panel()
        self.schema_panel = self._build_schema_panel()
        self.show_tab(DOCUMENTS_TAB)

    def _build_title(self) -> None:
        """Breadcrumb, collection name, subtitle, Import + Add document.

        Author: Archer
        """
        top = ctk.CTkFrame(self.main, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew")
        self._build_breadcrumb(top)
        make_label(top, self.page.collection, "title").pack(anchor="w",
                                                            pady=(12, 8))
        make_label(top, f"Browse and add documents in {self._namespace()}.",
                   "subtitle").pack(anchor="w")
        buttons = ctk.CTkFrame(top, fg_color="transparent")
        buttons.place(relx=1.0, rely=0.62, anchor="e")
        make_button(buttons, "Import JSON file", self.import_file).pack(
            side="left", padx=(0, 10))
        self.make_primary_button(buttons, "+  Add document",
                                 self.page.open_add_document).pack(side="left")

    def _build_breadcrumb(self, parent) -> None:
        """<cluster> / Databases / <database> / <collection>.

        Author: Archer
        """
        crumbs = ctk.CTkFrame(parent, fg_color="transparent")
        crumbs.pack(anchor="w")
        database = self.page.database
        links = ((self.cluster_name, self._actions.go_home),
                 ("Databases", self._actions.go_home),
                 (database, lambda: self._actions.open_database(database)))
        for text, command in links:
            link = make_label(crumbs, text, "secondary")
            link.configure(cursor="hand2")
            link.bind("<Button-1>", lambda _event, run=command: run())
            link.pack(side="left")
            make_label(crumbs, "  /  ", "secondary").pack(side="left")
        make_label(crumbs, self.page.collection, "secondary").pack(side="left")

    def _build_tabs(self) -> None:
        """Clickable "Documents N" and "Schema" tabs with a green underline.

        Author: Archer
        """
        bar = ctk.CTkFrame(self.main, fg_color="transparent")
        bar.grid(row=1, column=0, pady=(20, 16), sticky="ew")
        row = ctk.CTkFrame(bar, fg_color="transparent")
        row.pack(fill="x")
        names = [DOCUMENTS_TAB] + ([SCHEMA_TAB] if self.page.schema else [])
        for index, name in enumerate(names):
            tab = ctk.CTkFrame(row, fg_color="transparent")
            tab.pack(side="left", padx=(0 if index == 0 else 24, 0))
            label = make_label(tab, name, "body-bold")
            label.configure(cursor="hand2")
            label.bind("<Button-1>", lambda _event, n=name: self.show_tab(n))
            label.pack(pady=(0, 8))
            # tk.Frame: thin CTkFrames don't render.
            underline = tk.Frame(tab, height=2)
            underline.pack(fill="x")
            self.tabs[name] = (label, underline)
        tk.Frame(bar, height=1,
                 background=get_color("border/default")).pack(fill="x")

    def _build_documents_panel(self) -> ctk.CTkFrame:
        """Toolbar, document list, and footer.

        Author: Archer
        """
        panel = ctk.CTkFrame(self.main, fg_color="transparent")
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(1, weight=1)
        bar = ctk.CTkFrame(panel, fg_color="transparent")
        bar.grid(row=0, column=0, pady=(0, 16), sticky="ew")
        self.make_filter(bar, "Filter documents...").pack(side="left")
        self._refresh_button = make_button(bar, "Refresh", self.refresh)
        set_icon(self._refresh_button, REFRESH)
        self._refresh_button.pack(side="right")
        self.document_list = ctk.CTkScrollableFrame(
            panel, corner_radius=8, border_width=1,
            fg_color=get_color("surface/card"),
            border_color=get_color("border/default"))
        self.document_list.grid(row=1, column=0, sticky="nsew")
        self.empty_label = make_label(self.document_list,
                                      "No documents were found.", "secondary")
        self._build_footer(panel)
        return panel

    def _build_footer(self, panel) -> None:
        """ "Showing X of Y documents" left; import / error message right.

        Author: Archer
        """
        footer = ctk.CTkFrame(panel, fg_color="transparent")
        footer.grid(row=2, column=0, pady=(10, 0), sticky="ew")
        self.showing_label = make_label(footer, "Loading…", "muted")
        self.showing_label.pack(side="left")
        self.message_label = make_label(footer, "", "muted")
        self.message_label.pack(side="right")

    def _build_schema_panel(self) -> SchemaTab | None:
        """The Schema tab, or None when there's no schema support.

        Author: Archer
        """
        if self.page.schema is None:
            return None
        panel = SchemaTab(self.main, self.page.schema)
        # Saving or removing the schema changes which rows are marked.
        panel.on_change = self.refresh
        return panel

    # ----- tabs -----

    def show_tab(self, name: str) -> None:
        """Show one tab's panel and move the green underline to it.

        Author: Archer
        """
        panels = {DOCUMENTS_TAB: self.documents_panel,
                  SCHEMA_TAB: self.schema_panel}
        for tab_name, (label, underline) in self.tabs.items():
            active = tab_name == name
            color = "accent/primary" if active else "text/secondary"
            label.configure(text_color=get_color(color))
            underline.configure(background=get_color(
                "accent/primary" if active else "background/app"))
            if active:
                panels[tab_name].grid(row=5, column=0, sticky="nsew")
            else:
                panels[tab_name].grid_remove()
        self.active_tab = name

    # ----- documents -----

    def draw_documents(self) -> None:
        """Rebuild the rows, then re-apply the filter.

        Author: Archer (cards get an Edit button; broken ones marked red)
        """
        for row in self.rows:
            row.destroy()
        self.rows = []
        for document in self._documents:
            row = DocumentRow(self.document_list, document,
                              self.page.open_edit_document)
            if document.get("_id") in self._broken:
                row.mark_broken()
            self.rows.append(row)
        self.apply_filter()

    def apply_filter(self) -> None:
        """Hide rows whose text doesn't contain the filter (any case).

        Author: Archer
        """
        needle = self.filter_entry.get().strip().lower()
        shown = 0
        for row in self.rows:
            if needle in row.text.lower():
                row.pack(fill="x")
                shown += 1
            else:
                row.pack_forget()
        if shown:
            self.empty_label.pack_forget()
        else:
            self.empty_label.pack(pady=24)
        self._update_showing(shown)

    def _update_showing(self, shown: int) -> None:
        """ "Showing X of Y documents", plus the cap and mismatch count.

        Author: Archer
        """
        total = len(self._documents)
        text = f"Showing {shown} of {total} document{'' if total == 1 else 's'}"
        if total >= DOCUMENT_LIST_LIMIT:
            text += f" (newest {DOCUMENT_LIST_LIMIT})"
        broken = len(self._broken)
        if broken:
            verb = "doesn't" if broken == 1 else "don't"
            text += f" · {broken} {verb} match the schema"
        self.showing_label.configure(text=text)

    def import_file(self) -> None:
        """Add every document from a chosen JSON file, then reload.

        Author: Archer (moved onto the restyled page)
        """
        path = self._choose_file()
        if not path:
            return
        try:
            documents = parse_documents_json(read_text_file(path))
            result = self.page.add_documents(documents)
        except ValueError as error:
            self.show_message(str(error), is_error=True)
            return
        except PyMongoError:
            self.show_message(
                "Could not import the file. Check your permissions.", True)
            return
        self.show_message(_describe_import(result))
        self.refresh()

    def _choose_file(self) -> str:
        """Open the file picker. Returns "" if cancelled."""
        return filedialog.askopenfilename(
            title="Import JSON file",
            filetypes=[("JSON files", "*.json *.jsonl"), ("All files", "*.*")],
        )

    def show_message(self, text: str, is_error: bool = False) -> None:
        """Green success or red error, bottom right.

        Author: Archer
        """
        self.message_label.configure(text=text, text_color=get_color(
            "feedback/danger" if is_error else "accent/primary"))

    def _namespace(self) -> str:
        """Author: Archer"""
        return f"{self.page.database}.{self.page.collection}"

    # ----- ClusterPage hooks -----

    def load_page(self):
        """WORKER THREAD: sidebar names, documents, and which break the schema.

        Author: Archer
        """
        names = self._actions.list_database_names()
        documents = self.page.list_documents()
        return names, (documents, self._find_broken(documents))

    def _find_broken(self, documents: list[dict]) -> set:
        """WORKER THREAD: ids of these documents that break the schema.

        If the check fails, nothing is marked (the list still shows).

        Author: Archer
        """
        if self.page.find_mismatches is None or not documents:
            return set()
        ids = [document["_id"] for document in documents if "_id" in document]
        try:
            return self.page.find_mismatches(ids)
        except (ValueError, PyMongoError):
            return set()

    def show_page(self, page_data, status) -> None:
        """Redraw the tab count and the rows.

        Author: Archer
        """
        self._documents, self._broken = page_data
        label, _underline = self.tabs[DOCUMENTS_TAB]
        label.configure(text=f"{DOCUMENTS_TAB}  {len(self._documents)}")
        self.draw_documents()

    def on_load_failed(self) -> None:
        """Author: Archer"""
        self.showing_label.configure(text="")


class DocumentRow(ctk.CTkFrame):
    """One document as a card: the whole document as indented JSON colored
    like the JSON editor, and "✎ Edit" in the top-right corner. Call
    mark_broken() to tint it red with "Doesn't match schema".

    Author: Archer (pretty multi-line JSON + Edit button instead of a
    one-line preview)
    """

    def __init__(self, master, document: dict, on_edit=None) -> None:
        """`on_edit(document)` opens the Edit page; None hides Edit.

        Author: Archer
        """
        super().__init__(master, corner_radius=0,
                         fg_color=get_color("surface/card"))
        self.document = document
        self.text = format_document_pretty(document)  # also used by filter
        self.broken = False
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=12)
        inner.grid_columnconfigure(0, weight=1)
        self.preview = _make_preview(inner, self.text,
                                     get_color("surface/card"))
        self.preview.grid(row=0, column=0, sticky="ew")
        self._actions = ctk.CTkFrame(inner, fg_color="transparent")
        self._actions.grid(row=0, column=1, padx=(12, 0), sticky="ne")
        self.edit_button = None
        if on_edit is not None:
            self.edit_button = make_button(self._actions, "✎  Edit",
                                           lambda: on_edit(document))
            self.edit_button.configure(width=72, height=28, font=get_font(12))
            self.edit_button.pack(side="right")
        tk.Frame(self, height=1,
                 background=get_color("border/default")).pack(fill="x")

    def mark_broken(self) -> None:
        """Red tint + "⚠ Doesn't match schema" next to Edit.

        Author: Archer
        """
        self.broken = True
        background = get_color("feedback/danger-subtle")
        self.configure(fg_color=background)
        self.preview.configure(background=background)
        marker = make_label(self._actions, BROKEN_LABEL, "body-bold")
        marker.configure(text_color=get_color("feedback/danger"),
                         font=get_font(12, "bold"))
        marker.pack(side="right", padx=(0, 12))


def _make_preview(parent, text: str, background: str) -> tk.Text:
    """Read-only, multi-line JSON colored like the JSON editor
    (design/Add document.png): keys in normal text, values green, and
    brackets / commas grey.

    A tk.Text instead of a label because a label can only have one color.
    It's disabled so it can't be typed in, but text can still be selected
    and copied. It grows to fit every line (see _fit_height), so the
    document list is the only thing that scrolls.

    Author: Archer (multi-line, wraps long values)
    """
    # Plain tk.Text isn't DPI-scaled like CTk widgets, so scale the font
    # here (negative size = pixels), same as the JSON editor does.
    font = (get_font(13).cget("family"),
            -round(parent._apply_widget_scaling(13)))
    # width=1: take only the room the card gives it (the default 80
    # characters would push the Edit button off the card).
    preview = tk.Text(parent, height=text.count("\n") + 1, width=1,
                      wrap="char", font=font, borderwidth=0,
                      highlightthickness=0, takefocus=0, cursor="arrow",
                      background=background, spacing1=2, spacing3=2,
                      foreground=get_color("text/secondary"),
                      selectbackground=get_color("accent/subtle"))
    for tag, color_key in PREVIEW_COLORS.items():
        preview.tag_configure(tag, foreground=get_color(color_key))
    preview.insert("1.0", text)
    for match in TOKEN_PATTERN.finditer(text):
        preview.tag_add(match.lastgroup, f"1.0+{match.start()}c",
                        f"1.0+{match.end()}c")
    preview.configure(state="disabled")
    # Long values wrap onto extra lines once the width is known.
    preview.bind("<Configure>", lambda _event: _fit_height(preview))
    return preview


def _fit_height(preview: tk.Text) -> None:
    """Make the text box exactly as tall as its wrapped lines.

    Author: Archer
    """
    # Line breaks on screen between the first and last character, + 1.
    breaks = preview.count("1.0", "end-1c", "displaylines")
    # Older Pythons return a tuple (or None for 0); newer can return int.
    if isinstance(breaks, tuple):
        breaks = breaks[0]
    height = (breaks or 0) + 1
    if int(preview.cget("height")) != height:
        preview.configure(height=height)


def _describe_import(result: ImportResult) -> str:
    """Message with how many were added or skipped."""
    noun = "document" if result.inserted == 1 else "documents"
    text = f"Imported {result.inserted} {noun}."
    if result.skipped:
        text += f" {result.skipped} skipped (for example, a duplicate _id)."
    return text
