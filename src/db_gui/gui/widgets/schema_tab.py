"""Schema tab on the documents screen: view, edit, save, or remove a
collection's schema.

Author: Archer

Two views of the same schema, switched with the "Simplified / Raw JSON"
toggle (see expected-behavior.md > Documents Page > Schema tab):
- Simplified: one row per field (name, type, array of, required, min, max).
- Raw JSON: the actual $jsonSchema, editable.

Switching views converts between them, so edits in one show up in the other.
If the conversion fails (bad JSON, unsupported rules) the error is shown and
the view doesn't switch. Saving warns first when existing documents would
break the new schema. All MongoDB work goes through SchemaActions (db/).
"""

import json
from collections.abc import Callable
from dataclasses import dataclass

import customtkinter as ctk

from ...db.connection import PyMongoError
from ...db.schema import (FIELD_TYPES, SchemaField, build_schema,
                          parse_schema)
from .message_dialog import MessageSpec, show_dialog

SIMPLIFIED = "Simplified"
RAW_JSON = "Raw JSON"
ERROR_COLOR = "#d9534f"
SUCCESS_COLOR = "#2e8b57"


@dataclass
class SchemaActions:
    """The db/ functions the tab calls, already set up for one collection.

    Author: Archer
    """

    get_schema: Callable[[], dict | None]
    save_schema: Callable[[dict], None]
    remove_schema: Callable[[], None]
    count_mismatches: Callable[[dict], int]


class FieldRow(ctk.CTkFrame):
    """One editable field in the simplified view.

    Author: Archer
    """

    def __init__(self, master, field: SchemaField, on_remove: Callable) -> None:
        super().__init__(master, fg_color="transparent")
        self.name = ctk.CTkEntry(self, width=160, placeholder_text="Field name")
        self.type = ctk.CTkOptionMenu(self, values=list(FIELD_TYPES), width=110)
        self.is_array = ctk.CTkCheckBox(self, text="Array of", width=90)
        self.required = ctk.CTkCheckBox(self, text="Required", width=90)
        self.minimum = ctk.CTkEntry(self, width=70, placeholder_text="min")
        self.maximum = ctk.CTkEntry(self, width=70, placeholder_text="max")
        remove = ctk.CTkButton(self, text="✕", width=28,
                               command=lambda: on_remove(self))
        for column, widget in enumerate((self.name, self.is_array, self.type,
                                         self.required, self.minimum,
                                         self.maximum, remove)):
            widget.grid(row=0, column=column, padx=4, pady=3)
        self._fill(field)

    def _fill(self, field: SchemaField) -> None:
        """Put a field's values into the inputs.

        Author: Archer
        """
        self.name.insert(0, field.name)
        self.type.set(field.type)
        for checkbox, on in ((self.is_array, field.is_array),
                             (self.required, field.required)):
            checkbox.select() if on else checkbox.deselect()
        for entry, value in ((self.minimum, field.minimum),
                             (self.maximum, field.maximum)):
            if value is not None:
                entry.insert(0, str(value))

    def to_field(self) -> SchemaField:
        """Read the inputs back into a SchemaField.

        Raises ValueError if min/max isn't a number.

        Author: Archer
        """
        name = self.name.get().strip()
        return SchemaField(
            name=name, type=self.type.get(),
            required=bool(self.required.get()),
            is_array=bool(self.is_array.get()),
            minimum=_parse_limit(self.minimum.get(), name, "min"),
            maximum=_parse_limit(self.maximum.get(), name, "max"),
        )


class SchemaTab(ctk.CTkFrame):
    """The whole Schema tab.

    Author: Archer
    """

    def __init__(self, master, actions: SchemaActions) -> None:
        super().__init__(master, fg_color="transparent")
        self._actions = actions
        self.rows: list[FieldRow] = []
        self.has_schema = False
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_toggle()
        self._build_editors()
        self._build_buttons()
        self.load_schema()

    def _build_toggle(self) -> None:
        """Simplified / Raw JSON switch.

        Author: Archer
        """
        self.toggle = ctk.CTkSegmentedButton(
            self, values=[SIMPLIFIED, RAW_JSON], command=self._switch_view)
        self.toggle.set(SIMPLIFIED)
        self.toggle.grid(row=0, column=0, padx=10, pady=(10, 6), sticky="w")
        self.view = SIMPLIFIED

    def _build_editors(self) -> None:
        """The field list (+ Add field) and the JSON box. Only one is shown.

        Author: Archer
        """
        self.simplified = ctk.CTkFrame(self, fg_color="transparent")
        self.simplified.grid_columnconfigure(0, weight=1)
        self.simplified.grid_rowconfigure(0, weight=1)
        self.field_list = ctk.CTkScrollableFrame(self.simplified, height=260)
        self.field_list.grid(row=0, column=0, sticky="nsew")
        ctk.CTkButton(self.simplified, text="+ Add field", width=120,
                      command=self.add_row).grid(row=1, column=0, pady=6,
                                                 sticky="w")
        self.json_box = ctk.CTkTextbox(
            self, font=ctk.CTkFont(family="Courier", size=13))
        self.simplified.grid(row=1, column=0, padx=10, sticky="nsew")

    def _build_buttons(self) -> None:
        """Save schema / Remove schema and the message line.

        Author: Archer
        """
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.grid(row=2, column=0, padx=10, pady=(6, 0), sticky="ew")
        ctk.CTkButton(row, text="Save schema",
                      command=self.save).pack(side="left", padx=(0, 10))
        self.remove_button = ctk.CTkButton(row, text="Remove schema",
                                           command=self.remove)
        self.remove_button.pack(side="left")
        self.message = ctk.CTkLabel(self, text="", wraplength=640,
                                    justify="left")
        self.message.grid(row=3, column=0, padx=10, pady=6, sticky="w")

    def load_schema(self) -> None:
        """Get the schema from MongoDB and show it.

        A schema this version can't show opens in Raw JSON with the error.

        Author: Archer
        """
        try:
            schema = self._actions.get_schema()
        except (ValueError, PyMongoError) as error:
            self.show_message(f"Could not load the schema: {error}", True)
            return
        self.has_schema = schema is not None
        self._update_remove_button()
        self._set_json(schema)
        if schema is None:
            self.show_message("This collection has no schema yet. Add fields "
                              "and click Save schema.")
            return
        self._show_loaded(schema)

    def _show_loaded(self, schema: dict) -> None:
        """Fill the simplified view, or fall back to Raw JSON if unsupported.

        Author: Archer
        """
        try:
            self._set_rows(parse_schema(schema))
        except ValueError as error:
            self._show_view(RAW_JSON)
            self.show_message(str(error), True)

    def add_row(self, field: SchemaField | None = None) -> FieldRow:
        """Add one field row (blank string field by default).

        Author: Archer
        """
        row = FieldRow(self.field_list, field or SchemaField("", "string"),
                       self._remove_row)
        row.pack(fill="x")
        self.rows.append(row)
        return row

    def _remove_row(self, row: FieldRow) -> None:
        """Author: Archer"""
        self.rows.remove(row)
        row.destroy()

    def _set_rows(self, fields: list[SchemaField]) -> None:
        """Replace every row with `fields`.

        Author: Archer
        """
        for row in self.rows:
            row.destroy()
        self.rows = []
        for field in fields:
            self.add_row(field)

    def _set_json(self, schema: dict | None) -> None:
        """Replace the JSON box text (empty when there's no schema).

        Author: Archer
        """
        self.json_box.delete("1.0", "end")
        if schema is not None:
            self.json_box.insert("1.0", json.dumps(schema, indent=2))

    def current_schema(self) -> dict:
        """The schema from whichever view is showing.

        Raises ValueError (bad JSON, bad field, unsupported rule).

        Author: Archer
        """
        if self.view == SIMPLIFIED:
            fields = [row.to_field() for row in self.rows]
            if not fields:
                raise ValueError("Add at least one field.")
            return build_schema(fields)
        schema = _load_json(self.json_box.get("1.0", "end"))
        parse_schema(schema)
        return schema

    def _switch_view(self, target: str) -> None:
        """Convert the showing view into the other one, then swap.

        Author: Archer
        """
        if target == self.view:
            return
        try:
            self._convert_to(target)
        except ValueError as error:
            self.toggle.set(self.view)  # stay where we were
            self.show_message(str(error), True)
            return
        self._show_view(target)
        self.show_message("")

    def _convert_to(self, target: str) -> None:
        """Copy the current schema into the `target` view's inputs.

        An empty view converts to an empty other view.

        Author: Archer
        """
        if target == RAW_JSON:
            fields = [row.to_field() for row in self.rows]
            self._set_json(build_schema(fields) if fields else None)
            return
        text = self.json_box.get("1.0", "end")
        self._set_rows(parse_schema(_load_json(text)) if text.strip() else [])

    def _show_view(self, target: str) -> None:
        """Show one editor and hide the other.

        Author: Archer
        """
        shown, hidden = ((self.json_box, self.simplified) if target == RAW_JSON
                         else (self.simplified, self.json_box))
        hidden.grid_remove()
        shown.grid(row=1, column=0, padx=10, sticky="nsew")
        self.toggle.set(target)
        self.view = target

    def save(self) -> None:
        """Check the schema, warn about broken documents, then save.

        Author: Archer
        """
        try:
            schema = self.current_schema()
            if not self._confirm_mismatches(schema):
                return
            self._actions.save_schema(schema)
        except ValueError as error:
            self.show_message(str(error), True)
            return
        except PyMongoError as error:
            self.show_message(f"Could not save the schema: {error}", True)
            return
        self.has_schema = True
        self._update_remove_button()
        self.show_message("Schema saved.")

    def _confirm_mismatches(self, schema: dict) -> bool:
        """Ask before saving when existing documents would break the schema.

        Author: Archer
        """
        count = self._actions.count_mismatches(schema)
        if count == 0:
            return True
        noun = "document doesn't" if count == 1 else "documents don't"
        return show_dialog(self, MessageSpec(
            title="Save schema", kind="question",
            heading=f"{count} {noun} match this schema.",
            message="They will be kept, but can't be updated until they're "
                    "fixed. Save anyway?"))

    def remove(self) -> None:
        """Ask, then remove the schema so the collection is free-form.

        Author: Archer
        """
        if not show_dialog(self, MessageSpec(
                title="Remove schema", kind="question",
                heading="Remove this collection's schema?",
                message="Documents will no longer be checked.")):
            return
        try:
            self._actions.remove_schema()
        except (ValueError, PyMongoError) as error:
            self.show_message(f"Could not remove the schema: {error}", True)
            return
        self.has_schema = False
        self._update_remove_button()
        self.show_message("Schema removed. The collection is free-form again.")

    def _update_remove_button(self) -> None:
        """Remove schema only works when there is one.

        Author: Archer
        """
        self.remove_button.configure(
            state="normal" if self.has_schema else "disabled")

    def show_message(self, text: str, is_error: bool = False) -> None:
        """Red error or green success line under the buttons.

        Author: Archer
        """
        self.message.configure(
            text=text, text_color=ERROR_COLOR if is_error else SUCCESS_COLOR)


def _parse_limit(text: str, name: str, which: str) -> int | float | None:
    """"" -> None, "5" -> 5, "2.5" -> 2.5, anything else -> ValueError.

    Author: Archer
    """
    text = text.strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        raise ValueError(f"Field '{name}' {which} must be a number.") from None


def _load_json(text: str) -> dict:
    """Parse the Raw JSON box, with a readable error.

    Author: Archer
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON: {error.msg} (line {error.lineno}, "
                         f"column {error.colno}).") from error
