"""In-app replacement for tkinter.messagebox, styled after
design/Rename confirm popups.png.

Author: Archer

Layout: a header (database icon, title, ✕), a body with a round badge
("?", "i", or "!") next to an optional bold heading and the message, then
the buttons. Questions get Yes (green) + No; everything else gets OK.

Use show_dialog(parent, MessageSpec(...)), which blocks until the pop-up
closes and returns True for Yes/OK.
"""

import tkinter as tk
from dataclasses import dataclass

import customtkinter as ctk

from ..theme import get_color, get_font
from .icons import create_icon_canvas, draw_database_glyph
from .labels import make_label
from .modal import ModalCard

BADGE_SIZE = 44
TEXT_WIDTH = 440  # wrap width for the message, beside the badge
# kind -> (badge glyph, glyph color key, badge fill color key)
KINDS = {
    "question": ("?", "accent/primary", "accent/badge"),
    "info": ("i", "accent/primary", "accent/badge"),
    "warning": ("!", "feedback/warning", "feedback/warning-subtle"),
    "error": ("!", "feedback/danger", "feedback/danger-subtle"),
}


@dataclass
class MessageSpec:
    """What the pop-up says (keeps MessageDialog under 3 arguments)."""

    title: str
    message: str
    kind: str = "info"  # a KINDS key
    heading: str = ""  # optional bold line above the message


class MessageDialog(ModalCard):
    """Modal message with OK, or Yes/No for kind="question"."""

    WIDTH = 600

    def __init__(self, master, spec: MessageSpec) -> None:
        """Author: Archer"""
        super().__init__(master)
        self._spec = spec
        self.result = False  # True only when Yes/OK was clicked
        self._build_header()
        _divider(self)
        self._build_body()
        _divider(self)
        primary = self._build_buttons()
        self.bind("<Return>", lambda _event: self._finish(True))
        self.bind("<Escape>", lambda _event: self._finish(False))
        self.finish_setup(primary)

    def _build_header(self) -> None:
        """Database icon, title, and the ✕ close button.

        Author: Archer
        """
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=(20, 14), pady=12)
        icon = create_icon_canvas(header, 24, get_color("surface/card"))
        draw_database_glyph(icon, get_color("accent/primary"))
        icon.pack(side="left", padx=(0, 12))
        make_label(header, self._spec.title, "dialog-title").pack(side="left")
        ctk.CTkButton(
            header, text="✕", width=28, height=28, fg_color="transparent",
            hover_color=get_color("state/hover"), font=get_font(14),
            text_color=get_color("text/primary"),
            command=lambda: self._finish(False),
        ).pack(side="right")

    def _build_body(self) -> None:
        """Round badge on the left; heading + message on the right.

        Author: Archer
        """
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="x", padx=24, pady=20)
        self.badge = _make_badge(body, self._spec.kind)
        self.badge.pack(side="left", anchor="n", padx=(0, 20))
        text = ctk.CTkFrame(body, fg_color="transparent")
        text.pack(side="left", fill="x", expand=True)
        if self._spec.heading:
            heading = make_label(text, self._spec.heading, "body-bold")
            heading.configure(font=get_font(15, "bold"))
            heading.pack(anchor="w", pady=(0, 10))
        self.message_label = make_label(text, self._spec.message, "body")
        self.message_label.configure(wraplength=TEXT_WIDTH, justify="left")
        self.message_label.pack(anchor="w")

    def _build_buttons(self) -> ctk.CTkButton:
        """Yes + No for questions, otherwise OK. Returns the green button.

        Author: Archer
        """
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=16)
        common = {"height": 36, "width": 120, "corner_radius": 6,
                  "font": get_font(13, "bold")}
        self.buttons = []  # kept for tests / future keyboard navigation
        if self._spec.kind == "question":
            self.buttons.append(ctk.CTkButton(
                row, text="No", command=lambda: self._finish(False),
                fg_color=get_color("button/secondary-fill"),
                hover_color=get_color("state/hover"), border_width=1,
                border_color=get_color("border/default"),
                text_color=get_color("text/primary"), **common))
            self.buttons[-1].pack(side="right")
        primary = ctk.CTkButton(
            row, text="Yes" if self._spec.kind == "question" else "OK",
            command=lambda: self._finish(True),
            fg_color=get_color("button/fill"),
            hover_color=get_color("button/fill-hover"),
            text_color=get_color("button/text"), **common)
        primary.pack(side="right", padx=(0, 12) if self._spec.kind == "question"
                     else 0)
        self.buttons.insert(0, primary)
        return primary

    def _finish(self, result: bool) -> None:
        """Record which button was clicked and close.

        Author: Archer
        """
        self.result = result
        self.close()


def _divider(parent) -> None:
    """Full-width 1px line (tk.Frame: a 1px CTkFrame doesn't render).

    Author: Archer
    """
    tk.Frame(parent, height=1, background=get_color("border/default")).pack(
        fill="x")


def _make_badge(parent, kind: str) -> tk.Canvas:
    """Filled circle with a "?", "i", or "!" in the middle.

    Author: Archer
    """
    glyph, glyph_key, fill_key = KINDS[kind]
    canvas = create_icon_canvas(parent, BADGE_SIZE, get_color("surface/card"))
    canvas.create_oval(1, 1, BADGE_SIZE - 1, BADGE_SIZE - 1,
                       fill=get_color(fill_key), outline="")
    canvas.create_text(BADGE_SIZE / 2, BADGE_SIZE / 2, text=glyph,
                       fill=get_color(glyph_key), font=get_font(20, "bold"))
    return canvas


def show_dialog(parent, spec: MessageSpec) -> bool:
    """Show the pop-up and wait for it to close.

    Returns True if the user clicked Yes/OK, False for No, ✕, or Esc.

    Author: Archer
    """
    dialog = MessageDialog(parent, spec)
    dialog.wait_window()
    return dialog.result
