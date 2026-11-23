"""Styled pop-up form, matching design/Create database — pop-up.png and
design/Rename database — pop-up.png.

Author: Archer

Layout: title + × close, subtitle, one or more labeled text boxes (each with
a hint under it), an error line, then Cancel and a primary button. The window
behind is dimmed while the pop-up is open (see modal.py, shared with
MessageDialog).

Two ways to use it:
- on_submit(values) -> error text or None. Returning text keeps the pop-up
  open and shows the error (e.g. the server refused the name).
- wait_for_values() blocks until it closes and returns the values, or None
  if the user cancelled.
"""

import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass, field

import customtkinter as ctk

from ..theme import get_color, get_font
from .labels import make_label
from .modal import ModalCard

DIALOG_WIDTH = ModalCard.WIDTH


@dataclass
class FormField:
    """One text box in the form."""

    label: str
    placeholder: str = ""
    hint: str = ""
    initial: str = ""


@dataclass
class FormSpec:
    """Everything the pop-up shows (keeps FormDialog under 3 arguments)."""

    title: str
    subtitle: str
    submit_text: str
    fields: list[FormField] = field(default_factory=list)


class FormDialog(ModalCard):
    """Modal pop-up form with a dimmed backdrop."""

    def __init__(self, master, spec: FormSpec,
                 on_submit: Callable[[list[str]], str | None] | None = None):
        """Author: Archer (shared pop-up behavior moved to ModalCard)"""
        super().__init__(master)
        self._spec = spec
        self._on_submit = on_submit or (lambda _values: None)
        self.values: list[str] | None = None
        self._entries = self._build_form()
        self._build_buttons()
        self.bind("<Return>", lambda _event: self.submit())
        self.bind("<Escape>", lambda _event: self.cancel())
        self.finish_setup(self._entries[0] if self._entries else None)

    def _build_form(self) -> list[ctk.CTkEntry]:
        """Title row, subtitle, fields, and the (hidden) error line.

        Author: Archer
        """
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="x", padx=24, pady=(22, 4))
        title_row = ctk.CTkFrame(body, fg_color="transparent")
        title_row.pack(fill="x")
        make_label(title_row, self._spec.title, "dialog-title").pack(
            side="left")
        ctk.CTkButton(
            title_row, text="✕", width=28, height=28, fg_color="transparent",
            hover_color=get_color("state/hover"), font=get_font(14),
            text_color=get_color("text/primary"), command=self.cancel,
        ).pack(side="right")
        make_label(body, self._spec.subtitle, "subtitle").pack(
            anchor="w", pady=(6, 18))
        entries = [self._add_field(body, spec) for spec in self._spec.fields]
        self._error_label = make_label(body, "", "error")
        self._error_label.configure(wraplength=DIALOG_WIDTH - 48,
                                    justify="left")
        self._body = body
        return entries

    def _add_field(self, parent, spec: FormField) -> ctk.CTkEntry:
        """Bold label, text box (accent border), and grey hint.

        Author: Archer
        """
        make_label(parent, spec.label, "label").pack(anchor="w", pady=(0, 8))
        entry = ctk.CTkEntry(
            parent, height=40, corner_radius=4, border_width=1,
            fg_color=get_color("background/app"),
            border_color=get_color("accent/primary"),
            text_color=get_color("textbox/text"),
            placeholder_text=spec.placeholder or None,
            placeholder_text_color=get_color("textbox/placeholder"),
            font=get_font(13))
        if spec.initial:
            entry.insert(0, spec.initial)
        entry.pack(fill="x")
        make_label(parent, spec.hint, "secondary").pack(
            anchor="w", pady=(6, 14))
        return entry

    def _build_buttons(self) -> None:
        """Divider, then Cancel + the primary button on the right.

        Author: Archer
        """
        # Plain tk.Frame: a 1px CTkFrame doesn't render.
        tk.Frame(self, height=1, background=get_color("border/default")).pack(
            fill="x")
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=24, pady=18)
        common = {"height": 36, "corner_radius": 6, "font": get_font(13, "bold")}
        ctk.CTkButton(
            row, text=self._spec.submit_text, command=self.submit,
            fg_color=get_color("button/fill"),
            hover_color=get_color("button/fill-hover"),
            text_color=get_color("button/text"), width=84, **common,
        ).pack(side="right")
        ctk.CTkButton(
            row, text="Cancel", command=self.cancel, width=84,
            fg_color=get_color("button/secondary-fill"),
            hover_color=get_color("state/hover"), border_width=1,
            border_color=get_color("border/default"),
            text_color=get_color("text/primary"), **common,
        ).pack(side="right", padx=(0, 12))

    def show_error(self, message: str) -> None:
        """Show an error inside the pop-up, under the fields.

        Author: Archer
        """
        self._error_label.configure(text=message)
        self._error_label.pack(anchor="w", pady=(0, 4))

    def submit(self) -> None:
        """Check every field is filled, run on_submit, close if it worked.

        Author: Archer
        """
        values = [entry.get().strip() for entry in self._entries]
        for spec, value in zip(self._spec.fields, values):
            if not value:
                self.show_error(f"{spec.label} is required.")
                return
        error = self._on_submit(values)
        if error:
            self.show_error(error)
            return
        self.values = values
        self.close()

    def cancel(self) -> None:
        """Close without values. Author: Archer"""
        self.values = None
        self.close()

    def wait_for_values(self) -> list[str] | None:
        """Block until the pop-up closes; return the values or None.

        Author: Archer
        """
        self.wait_window()
        return self.values

