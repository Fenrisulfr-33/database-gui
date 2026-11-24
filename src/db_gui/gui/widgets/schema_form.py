"""Form built from a collection's schema, for the Add document page.

Author: Archer

Replaces the JSON editor when the collection has a schema (see
expected-behavior.md > Documents Page > Insert / edit form). One input per
field, matched to its type:
- string / numbers / date / ObjectId: a text box (dates as YYYY-MM-DD)
- bool: a true / false menu (plus an empty choice when optional)
- array of X: a list of text boxes with "+ Add item" and ✕ per item
An `_id` box comes first (leave it empty and MongoDB makes one), unless the
schema defines `_id` itself.

get_document() converts every input with utils/validators.py. Anything bad
is marked with a red border and a message under it, and nothing is returned
until it's all fixed.
"""

from collections.abc import Callable

import customtkinter as ctk

from ...db.schema import SchemaField
from ...utils.validators import (parse_array_values, parse_field_value,
                                 parse_id_text)
from ..theme import get_color, get_font
from .labels import make_label

PLACEHOLDERS = {
    "string": "Text", "int": "Whole number", "long": "Whole number",
    "double": "Number", "decimal": "Number", "date": "YYYY-MM-DD",
    "objectId": "24-character hex",
}
ID_FIELD = SchemaField("_id", "objectId")  # only used for its label + hint
ID_PLACEHOLDER = "ObjectId hex, or any text"


class SchemaForm(ctk.CTkFrame):
    """Bordered card: header, then one FieldInput per field.

    Author: Archer
    """

    def __init__(self, master, fields: list[SchemaField],
                 on_submit: Callable) -> None:
        super().__init__(master, corner_radius=8, border_width=1,
                         fg_color=get_color("surface/card"),
                         border_color=get_color("border/default"))
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_header(len(fields))
        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, padx=8, pady=(0, 8), sticky="nsew")
        self.inputs: list[FieldInput] = []
        if not any(field.name == "_id" for field in fields):
            self.inputs.append(IdInput(body, ID_FIELD, on_submit))
        self.inputs += [FieldInput(body, field, on_submit) for field in fields]
        for field_input in self.inputs:
            field_input.pack(fill="x", padx=8, pady=(10, 0))

    def _build_header(self, count: int) -> None:
        """"Schema form  N fields".

        Author: Archer
        """
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=16, pady=10, sticky="ew")
        make_label(header, "▤", "body-bold").pack(side="left", padx=(0, 12))
        make_label(header, "Schema form", "body-bold").pack(side="left")
        noun = "field" if count == 1 else "fields"
        make_label(header, f"{count} {noun}", "muted").pack(side="left",
                                                           padx=16)

    def get_document(self) -> dict:
        """Every input converted, as a document ready to insert.

        Marks bad inputs red. Raises ValueError if any are bad.

        Author: Archer
        """
        document, failed = {}, False
        for field_input in self.inputs:
            try:
                value = field_input.read()
            except ValueError as error:
                field_input.show_error(str(error))
                failed = True
                continue
            field_input.show_error("")
            if not (field_input.skip_when_empty and value is None):
                document[field_input.field.name] = value
        if failed:
            raise ValueError("Fix the fields marked in red.")
        return document


class FieldInput(ctk.CTkFrame):
    """Label + hint, the input(s) for one field, and an error line.

    Author: Archer
    """

    skip_when_empty = False  # empty optional fields are saved as null

    def __init__(self, master, field: SchemaField, on_submit: Callable) -> None:
        super().__init__(master, fg_color="transparent")
        self.field = field
        self._on_submit = on_submit
        title = ctk.CTkFrame(self, fg_color="transparent")
        title.pack(fill="x")
        make_label(title, field.name, "body-bold").pack(side="left")
        if field.required:
            required = make_label(title, " *", "body-bold")
            required.configure(text_color=get_color("feedback/danger"))
            required.pack(side="left")
        make_label(title, self.hint(), "muted").pack(side="left", padx=12)
        self.items: list[ctk.CTkEntry] = []
        self._build_input()
        self.error = make_label(self, "", "error")

    def hint(self) -> str:
        """e.g. "array of int · optional · 1–5 items".

        Author: Archer
        """
        field = self.field
        parts = [f"array of {field.type}" if field.is_array else field.type,
                 "required" if field.required else "optional"]
        limits = _limits_text(field)
        if limits:
            parts.append(limits)
        return " · ".join(parts)

    def _build_input(self) -> None:
        """The right widget(s) for the field's type.

        Author: Archer
        """
        if self.field.is_array:
            self._items_frame = ctk.CTkFrame(self, fg_color="transparent")
            self._items_frame.pack(fill="x")
            ctk.CTkButton(self, text="+ Add item", width=100, height=26,
                          fg_color="transparent", border_width=1,
                          border_color=get_color("border/default"),
                          hover_color=get_color("state/hover"),
                          text_color=get_color("text/secondary"),
                          font=get_font(12), command=self.add_item).pack(
                anchor="w", pady=(6, 0))
            return
        if self.field.type == "bool":
            choices = ["true", "false"] if self.field.required else [
                "", "true", "false"]
            self.entry = ctk.CTkOptionMenu(
                self, values=choices, width=140, font=get_font(13),
                fg_color=get_color("button/secondary-fill"),
                button_color=get_color("button/secondary-fill"),
                button_hover_color=get_color("state/hover"),
                text_color=get_color("text/primary"))
            self.entry.set(choices[0])
        else:
            self.entry = self._make_entry(self)
        self.entry.pack(anchor="w", pady=(6, 0))

    def _make_entry(self, parent) -> ctk.CTkEntry:
        """A text box with a type hint and Ctrl+Enter to insert.

        Author: Archer
        """
        entry = ctk.CTkEntry(
            parent, width=360, height=34, font=get_font(13),
            placeholder_text=self.placeholder(),
            fg_color=get_color("background/editor"),
            border_color=get_color("border/default"),
            text_color=get_color("textbox/text"),
            placeholder_text_color=get_color("text/muted"))
        entry.bind("<Control-Return>", lambda _event: self._on_submit())
        return entry

    def placeholder(self) -> str:
        """Grey hint inside the text box.

        Author: Archer
        """
        return PLACEHOLDERS[self.field.type]

    def add_item(self, text: str = "") -> ctk.CTkEntry:
        """One more array item (text box + ✕).

        Author: Archer
        """
        row = ctk.CTkFrame(self._items_frame, fg_color="transparent")
        row.pack(fill="x", pady=(6, 0))
        entry = self._make_entry(row)
        entry.insert(0, text)
        entry.pack(side="left")
        ctk.CTkButton(row, text="✕", width=28, fg_color="transparent",
                      hover_color=get_color("state/hover"),
                      command=lambda: self._remove_item(row, entry)).pack(
            side="left", padx=6)
        self.items.append(entry)
        return entry

    def _remove_item(self, row, entry) -> None:
        """Author: Archer"""
        self.items.remove(entry)
        row.destroy()

    def read(self):
        """The field's value in its type. Raises ValueError.

        Author: Archer
        """
        if self.field.is_array:
            return parse_array_values(self.field,
                                      [item.get() for item in self.items])
        return parse_field_value(self.field, self.entry.get())

    def show_error(self, message: str) -> None:
        """Red message + red borders, or clear them when message is "".

        Author: Archer
        """
        color = get_color("feedback/danger" if message else "border/default")
        for entry in self.items or [getattr(self, "entry", None)]:
            if isinstance(entry, ctk.CTkEntry):
                entry.configure(border_color=color)
        self.error.configure(text=message)
        if message:
            self.error.pack(anchor="w", pady=(4, 0))
        else:
            self.error.pack_forget()


class IdInput(FieldInput):
    """The optional _id box at the top of the form.

    Author: Archer
    """

    skip_when_empty = True  # leave _id out so MongoDB generates one

    def hint(self) -> str:
        """Author: Archer"""
        return "optional · leave empty to generate an ObjectId"

    def placeholder(self) -> str:
        """Author: Archer"""
        return ID_PLACEHOLDER

    def read(self):
        """Author: Archer"""
        return parse_id_text(self.entry.get())


def _limits_text(field: SchemaField) -> str:
    """"1–50 characters", "min 0", "max 5 items", or "" with no limits.

    Author: Archer
    """
    unit = ("items" if field.is_array else
            "characters" if field.type == "string" else "")
    low, high = field.minimum, field.maximum
    if low is None and high is None:
        return ""
    if low is not None and high is not None:
        text = f"{low}–{high}"
    else:
        text = f"min {low}" if high is None else f"max {high}"
    return f"{text} {unit}".strip()
