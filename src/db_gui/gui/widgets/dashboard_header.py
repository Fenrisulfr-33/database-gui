"""Top bar of the dashboard, styled after design/Dashboard.png.

Author: Archer

Per expected-behavior.md the header doesn't work yet: the workspace picker,
search box, help button, and avatar are drawn normally but disabled, so each
can be switched on as its feature lands. Only the Docs link works.
"""

import tkinter as tk
import webbrowser

import customtkinter as ctk

from ..assets import BRAND_MARK, load_image
from ..theme import get_color, get_font
from .labels import make_button, make_label

DOCS_URL = "https://www.mongodb.com/docs/"
HEADER_HEIGHT = 58


class DashboardHeader(ctk.CTkFrame):
    """Brand, (disabled) workspace + search, and the Docs link."""

    def __init__(self, master, username: str) -> None:
        """Author: Archer"""
        super().__init__(master, height=HEADER_HEIGHT, corner_radius=0,
                         fg_color=get_color("surface/chrome"))
        self._username = username
        self.grid_propagate(False)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(2, weight=1)
        self._build_brand()
        self._build_disabled_controls()
        self._build_right_side()

    def _build_brand(self) -> None:
        """Brand mark + "Arrow_>" at the far left.

        Author: Archer
        """
        brand = ctk.CTkFrame(self, fg_color="transparent")
        brand.grid(row=0, column=0, padx=(24, 32))
        # Keep a reference so Tk doesn't garbage-collect the image.
        self._brand_mark = load_image(BRAND_MARK, self)
        tk.Label(brand, image=self._brand_mark, borderwidth=0,
                 background=get_color("surface/chrome")).pack(
            side="left", padx=(0, 10))
        make_label(brand, "Arrow_>", "brand").pack(side="left")

    def _build_disabled_controls(self) -> None:
        """Workspace picker and global search: placeholders for now.

        Author: Archer
        """
        self.workspace_button = make_button(self, "Workspace  ▾")
        self.workspace_button.configure(fg_color="transparent", border_width=0)
        self.workspace_button.grid(row=0, column=1, padx=(0, 24))
        self.search_entry = ctk.CTkEntry(
            self, width=360, height=32, corner_radius=6, border_width=1,
            fg_color=get_color("background/app"),
            border_color=get_color("border/default"),
            placeholder_text="Search databases, collections...",
            placeholder_text_color=get_color("textbox/placeholder"),
            font=get_font(12))
        self.search_entry.configure(state="disabled")
        self.search_entry.grid(row=0, column=2, sticky="w")

    def _build_right_side(self) -> None:
        """Help (disabled), the working Docs link, and avatar (disabled).

        Author: Archer
        """
        right = ctk.CTkFrame(self, fg_color="transparent")
        right.grid(row=0, column=3, padx=24)
        self.help_button = make_button(right, "?")
        self.help_button.configure(width=30, fg_color="transparent",
                                   border_width=0)
        self.help_button.pack(side="left", padx=(0, 12))
        docs = make_label(right, "Docs ↗", "secondary")
        docs.configure(cursor="hand2")
        docs.bind("<Button-1>", lambda _event: webbrowser.open(DOCS_URL))
        docs.pack(side="left", padx=(0, 16))
        # Avatar shows the logged-in user's first two letters.
        initials = (self._username[:2] or "?").upper()
        self.avatar_button = make_button(right, initials)
        self.avatar_button.configure(width=32, height=32, corner_radius=16)
        self.avatar_button.pack(side="left")
