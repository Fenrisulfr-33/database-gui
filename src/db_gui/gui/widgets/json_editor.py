"""JSON editor card for the Add document page, styled after
design/Add document.png.

Author: Archer

Header: "{ }  JSON editor  Extended JSON" and a Format JSON button.
Body: line-number gutter + the text box, with syntax colors (keys, strings,
literals) and the cursor's line highlighted.
Footer: "✓ Valid document" or the JSON error, then "Ln x, Col y · UTF-8 ·
size".

The text is checked on every change with the same parser the old Add
document pop-up used (utils/validators.py), so Extended JSON like
{"$oid": "..."} and {"$date": "..."} works. `on_change(is_valid)` tells the
page so it can enable/disable Insert document.
"""

import json
import re
import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk

from ...utils.formatters import format_bytes
from ...utils.validators import parse_document_json
from ..theme import get_color, get_font
from .labels import make_label

# starting text so the user types between the braces
JSON_TEMPLATE = "{\n  \n}"
INDENT = "  "
# One regex for every colored token. A string followed by ":" is a key.
TOKEN_PATTERN = re.compile(
    r'(?P<key>"(?:\\.|[^"\\])*"(?=\s*:))'
    r'|(?P<string>"(?:\\.|[^"\\])*")'
    r'|(?P<literal>\b(?:true|false|null)\b|-?\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b)'
)
# token group -> palette color key
TOKEN_COLORS = {"key": "text/field-key", "string": "accent/primary",
                "literal": "feedback/info"}


class JsonEditor(ctk.CTkFrame):
    """Bordered card with the code editor.

    Author: Archer
    """

    def __init__(self, master, on_change: Callable[[bool], None]) -> None:
        super().__init__(master, corner_radius=8, border_width=1,
                         fg_color=get_color("surface/card"),
                         border_color=get_color("border/default"))
        self._on_change = on_change
        self.error = ""  # "" when the text is a valid document
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self._build_header()
        _divider(self, row=1)
        self._build_body()
        _divider(self, row=3)
        self._build_footer()
        self.set_text(JSON_TEMPLATE)
        self.text.mark_set("insert", "2.2")  # cursor between the braces

    def _build_header(self) -> None:
        """"{ }  JSON editor  Extended JSON" ... Format JSON.

        Author: Archer
        """
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=16, pady=10, sticky="ew")
        make_label(header, "{ }", "body-bold").pack(side="left", padx=(0, 12))
        make_label(header, "JSON editor", "body-bold").pack(side="left")
        make_label(header, "Extended JSON", "muted").pack(side="left", padx=16)
        self.format_button = ctk.CTkButton(
            header, text="≡  Format JSON", width=120, height=26,
            fg_color="transparent", hover_color=get_color("state/hover"),
            text_color=get_color("text/secondary"), font=get_font(12),
            command=self.format_json)
        self.format_button.pack(side="right")

    def _build_body(self) -> None:
        """Line-number gutter, text box, and scrollbar.

        Author: Archer
        """
        body = tk.Frame(self, background=get_color("background/editor"))
        body.grid(row=2, column=0, padx=1, sticky="nsew")
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)
        # Plain tk.Text isn't DPI-scaled like CTk widgets, so scale the font
        # here (negative size = pixels, which is what CTk uses too).
        font = (get_font(13).cget("family"),
                -round(self._apply_widget_scaling(13)))
        common = {"font": font, "borderwidth": 0,
                  "highlightthickness": 0, "pady": 12,
                  "background": get_color("background/editor"),
                  "spacing1": 3, "spacing3": 3}
        self.gutter = tk.Text(body, width=4, padx=8, takefocus=0,
                              foreground=get_color("text/muted"), **common)
        self.gutter.tag_configure("right", justify="right")
        self.gutter.grid(row=0, column=0, sticky="ns")
        # Made before the text box, which reports its scroll position at once.
        self.scrollbar = ctk.CTkScrollbar(body, command=self._scroll_both)
        self.scrollbar.grid(row=0, column=2, sticky="ns")
        self.text = tk.Text(body, wrap="none", undo=True, padx=12,
                            foreground=get_color("text/secondary"),
                            insertbackground=get_color("text/primary"),
                            selectbackground=get_color("accent/subtle"),
                            yscrollcommand=self._on_scroll, **common)
        self.text.grid(row=0, column=1, sticky="nsew")
        self._configure_tags()
        self._bind_keys()

    def _configure_tags(self) -> None:
        """Colors for tokens and the current line.

        Author: Archer
        """
        for tag, color_key in TOKEN_COLORS.items():
            self.text.tag_configure(tag, foreground=get_color(color_key))
        self.text.tag_configure("current_line",
                                background=get_color("state/highlight"))
        self.text.tag_lower("current_line")

    def _bind_keys(self) -> None:
        """Refresh on edits / cursor moves, and Tab inserts two spaces.

        Author: Archer
        """
        self.text.bind("<<Modified>>", self._on_modified)
        for event in ("<KeyRelease>", "<ButtonRelease-1>"):
            self.text.bind(event, lambda _event: self._update_cursor())
        self.text.bind("<Tab>", self._insert_indent)

    def _build_footer(self) -> None:
        """Validity on the left; Ln/Col, encoding, and size on the right.

        Author: Archer
        """
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=4, column=0, padx=16, pady=6, sticky="ew")
        self.validity = make_label(footer, "", "secondary")
        self.validity.configure(font=get_font(11))
        self.validity.pack(side="left")
        self.position = make_label(footer, "", "muted")
        self.position.pack(side="right")

    # ----- reading / writing -----

    def get_text(self) -> str:
        """Author: Archer"""
        return self.text.get("1.0", "end-1c")

    def set_text(self, text: str) -> None:
        """Replace everything in the editor.

        Author: Archer
        """
        self.text.delete("1.0", "end")
        self.text.insert("1.0", text)
        self.refresh()

    def get_document(self) -> dict:
        """The typed document as a dict. Raises ValueError if invalid.

        Author: Archer
        """
        return parse_document_json(self.get_text())

    def format_json(self) -> None:
        """Re-indent the JSON (2 spaces). Leaves invalid JSON alone.

        Plain json (not bson) so Extended JSON like {"$oid": ...} stays as
        typed instead of being converted.

        Author: Archer
        """
        try:
            data = json.loads(self.get_text())
        except json.JSONDecodeError:
            return
        self.set_text(json.dumps(data, indent=2, ensure_ascii=False))

    # ----- refreshing -----

    def _on_modified(self, _event=None) -> None:
        """Tk fires <<Modified>> once until the flag is reset.

        Author: Archer
        """
        if self.text.edit_modified():
            self.text.edit_modified(False)
            self.refresh()

    def refresh(self) -> None:
        """Redo line numbers, colors, validity, and the cursor line.

        Author: Archer
        """
        self._update_gutter()
        self._highlight()
        self._validate()
        self._update_cursor()

    def _update_gutter(self) -> None:
        """One number per line, kept scrolled with the text.

        Author: Archer
        """
        lines = int(self.text.index("end-1c").split(".")[0])
        self.gutter.configure(state="normal")
        self.gutter.delete("1.0", "end")
        self.gutter.insert("1.0", "\n".join(str(n) for n in range(1, lines + 1)),
                           "right")
        self.gutter.configure(state="disabled")
        self.gutter.yview_moveto(self.text.yview()[0])

    def _highlight(self) -> None:
        """Re-color every token (fast enough for document-sized text).

        Author: Archer
        """
        for tag in TOKEN_COLORS:
            self.text.tag_remove(tag, "1.0", "end")
        for match in TOKEN_PATTERN.finditer(self.get_text()):
            self.text.tag_add(match.lastgroup, f"1.0+{match.start()}c",
                              f"1.0+{match.end()}c")

    def _validate(self) -> None:
        """Check the text and update the footer + the page.

        Author: Archer
        """
        try:
            self.get_document()
            self.error = ""
        except ValueError as error:
            self.error = str(error)
        valid = not self.error
        self.validity.configure(
            text="✓  Valid document" if valid else f"✕  {self.error}",
            text_color=get_color("accent/primary" if valid
                                 else "feedback/danger"))
        self._on_change(valid)

    def _update_cursor(self) -> None:
        """Highlight the cursor's line and show Ln/Col + size.

        Author: Archer
        """
        line, column = self.text.index("insert").split(".")
        self.text.tag_remove("current_line", "1.0", "end")
        self.text.tag_add("current_line", f"{line}.0", f"{line}.0+1l")
        size = format_bytes(len(self.get_text().encode("utf-8")))
        self.position.configure(
            text=f"Ln {line}, Col {int(column) + 1}    UTF-8    {size}")

    # ----- scrolling / keys -----

    def _on_scroll(self, first: str, last: str) -> None:
        """Text scrolled: move the scrollbar and the gutter with it.

        Author: Archer
        """
        self.scrollbar.set(first, last)
        self.gutter.yview_moveto(first)

    def _scroll_both(self, *args) -> None:
        """Scrollbar dragged: scroll the text (gutter follows via _on_scroll).

        Author: Archer
        """
        self.text.yview(*args)

    def _insert_indent(self, _event=None) -> str:
        """Author: Archer"""
        self.text.insert("insert", INDENT)
        return "break"  # stop Tk moving focus to the next widget


def _divider(parent, row: int) -> None:
    """Full-width 1px line (tk.Frame: a 1px CTkFrame doesn't render).

    Author: Archer
    """
    tk.Frame(parent, height=1, background=get_color("border/default")).grid(
        row=row, column=0, padx=1, sticky="ew")
