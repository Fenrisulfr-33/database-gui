"""Cluster login view, styled after design/Login.png.

Author: Archer (restyled to match the Login design + palette in design/)

Every color comes from theme.get_color(), so switching palettes restyles this
screen without touching this file.
"""

import tkinter as tk
import webbrowser

import customtkinter as ctk

from ..assets import BRAND_MARK, load_image
from ..theme import get_color, get_font
from ..widgets.icons import create_icon_canvas, draw_eye_glyph

MONGODB_SIGNUP_URL = "https://www.mongodb.com/cloud/atlas/register"
FIELD_WIDTH = 360
FIELD_HEIGHT = 44
PASSWORD_MASK = "•"

# Named text styles: (palette color key, pixel size, weight).
TEXT_STYLES = {
    "brand": ("text/primary", 20, "bold"),
    "title": ("text/primary", 32, "bold"),
    "subtitle": ("text/secondary", 13, "normal"),
    "label": ("text/primary", 12, "bold"),
    "body": ("text/secondary", 12, "normal"),
    "link": ("accent/primary", 12, "bold"),
    "hint": ("text/muted", 11, "normal"),
    "error": ("feedback/danger", 12, "normal"),
}


class ConnectionView(ctk.CTkFrame):
    """Collect cluster credentials and report the login attempt."""

    def __init__(self, master: ctk.CTk, submit_login) -> None:
        super().__init__(
            master, fg_color=get_color("background/login"), corner_radius=0
        )
        self._submit_login = submit_login
        self._password_hidden = True
        self._build_layout()

    def _build_layout(self) -> None:
        """Center the brand + card, with hint text pinned to the bottom.

        Author: Archer
        """
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure((0, 1), weight=1)
        column = ctk.CTkFrame(self, fg_color="transparent")
        column.grid(row=0, column=0, columnspan=2, pady=20)
        self._build_brand(column)
        self._build_card(column)
        self._add_text(self, "You must know your cluster name to sign in.",
                       "hint").grid(
            row=1, column=0, padx=40, pady=(0, 24), sticky="w")
        self._add_text(self, "Tip: Lock any databases you don't want deleted",
                       "hint").grid(
            row=1, column=1, padx=40, pady=(0, 24), sticky="e")

    def _build_brand(self, parent) -> None:
        """Show the brand mark + "Arrow_>" row that sits above the card.

        Author: Archer (uses assets/brand_mark.png instead of a drawn icon)
        """
        brand = ctk.CTkFrame(parent, fg_color="transparent")
        brand.pack(pady=(0, 16))
        # Plain tk.Label: CTkLabel only takes CTkImage, which needs Pillow.
        # Keep a reference on self so the image isn't garbage-collected.
        self._brand_mark = load_image(BRAND_MARK, self)
        tk.Label(brand, image=self._brand_mark, borderwidth=0,
                 background=get_color("background/login")).pack(
            side="left", padx=(0, 10))
        self._add_text(brand, "Arrow_>", "brand").pack(
            side="left")

    def _build_card(self, parent) -> None:
        """Build the rounded login card holding the form.

        Author: Archer
        """
        card = ctk.CTkFrame(parent, corner_radius=24,
                            fg_color=get_color("surface/login-card"))
        card.pack()
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(padx=20, pady=(36, 36))
        self._add_text(body, "Login", "title").pack(
            anchor="w")
        self._add_text(body, "Pick up where you left off in your cluster.",
                       "subtitle").pack(anchor="w", pady=(4, 20))
        self._uri_entry = self._add_field(
            body, "Mongo Cluster", "cluster0.abcde.mongodb.net")
        self._username_entry = self._add_field(
            body, "Username", "db_username")
        self._password_entry = self._add_password_field(body)
        self._build_actions(body)

    def _add_text(self, parent, text: str, style: str) -> ctk.CTkLabel:
        """Create a label in one of TEXT_STYLES (caller packs/grids it).

        Author: Archer
        """
        color_key, size, weight = TEXT_STYLES[style]
        return ctk.CTkLabel(parent, text=text, font=get_font(size, weight),
                            text_color=get_color(color_key), height=0)

    def _add_field(self, parent, label: str, placeholder: str):
        """Add a bold field label with a themed text box under it.

        Author: Archer
        """
        self._add_text(parent, label, "label").pack(
            anchor="w", pady=(0, 8))
        entry = self._make_entry(parent, placeholder)
        entry.pack(pady=(0, 18))
        return entry

    def _make_entry(self, parent, placeholder: str) -> ctk.CTkEntry:
        """Create a text box whose border turns accent-colored on focus.

        Author: Archer
        """
        entry = ctk.CTkEntry(
            parent, width=FIELD_WIDTH, height=FIELD_HEIGHT, corner_radius=4,
            border_width=1, fg_color=get_color("textbox/fill"),
            border_color=get_color("textbox/border"),
            text_color=get_color("textbox/text"),
            placeholder_text=placeholder,
            placeholder_text_color=get_color("textbox/placeholder"),
            font=get_font(13),
        )
        entry.bind("<FocusIn>", lambda _event: entry.configure(
            border_color=get_color("textbox/focus-ring")))
        entry.bind("<FocusOut>", lambda _event: entry.configure(
            border_color=get_color("textbox/border")))
        # Enter in any field submits, same as clicking "Sign in".
        entry.bind("<Return>", lambda _event: self._submit())
        return entry

    def _add_password_field(self, parent) -> ctk.CTkEntry:
        """Add the password box with a clickable show/hide eye inside it.

        Author: Archer
        """
        self._add_text(parent, "Password", "label").pack(
            anchor="w", pady=(0, 8))
        holder = ctk.CTkFrame(parent, fg_color="transparent")
        holder.pack(pady=(0, 16))
        entry = self._make_entry(holder, "••••••••••••")
        entry.configure(show=PASSWORD_MASK)
        entry.pack()
        self._eye_icon = create_icon_canvas(entry, 20,
                                            get_color("textbox/fill"))
        draw_eye_glyph(self._eye_icon, get_color("text/secondary"), False)
        self._eye_icon.configure(cursor="hand2")
        self._eye_icon.bind("<Button-1>", self._toggle_password_visibility)
        self._eye_icon.place(relx=1.0, rely=0.5, x=-14, anchor="e")
        return entry

    def _toggle_password_visibility(self, _event=None) -> None:
        """Flip the password between dots and plain text.

        Author: Archer
        """
        self._password_hidden = not self._password_hidden
        self._password_entry.configure(
            show=PASSWORD_MASK if self._password_hidden else "")
        # Crossed eye = "click to hide", shown while the password is visible.
        draw_eye_glyph(self._eye_icon, get_color("text/secondary"),
                       not self._password_hidden)

    def _build_actions(self, parent) -> None:
        """Add remember-me, the error slot, Sign in, and the footer text.

        Author: Archer
        """
        self._add_remember_me(parent)
        # Error label is only packed while there is an error to show.
        self._error_label = self._add_text(parent, "", "error")
        self._error_label.configure(wraplength=FIELD_WIDTH, justify="left")
        self._sign_in_button = ctk.CTkButton(
            parent, text="Sign in  →", width=FIELD_WIDTH, height=FIELD_HEIGHT,
            corner_radius=4, font=get_font(14, "bold"),
            fg_color=get_color("button/fill"),
            hover_color=get_color("button/fill-hover"),
            text_color=get_color("button/text"), command=self._submit,
        )
        self._sign_in_button.pack()
        self._build_signup_prompt(parent)
        self._add_text(parent, "This is a powerful tool, use at your own risk.",
                       "hint").pack(anchor="w", pady=(24, 0))

    def _add_remember_me(self, parent) -> None:
        """Add the "Remember me" checkbox, checked by default.

        Visual only for now: nothing reads this value yet.

        Author: Archer
        """
        self._remember_me = ctk.CTkCheckBox(
            parent, text="Remember me", font=get_font(12),
            text_color=get_color("text/secondary"),
            fg_color=get_color("accent/primary"),
            hover_color=get_color("button/fill-hover"),
            border_color=get_color("border/default"),
            checkmark_color=get_color("accent/on-primary"),
            checkbox_width=18, checkbox_height=18, corner_radius=4,
            border_width=2,
        )
        self._remember_me.select()
        self._remember_me.pack(anchor="w", pady=(0, 20))

    def _build_signup_prompt(self, parent) -> None:
        """Add "Don't have a MongoDB account? Create an account" link row.

        Author: Archer
        """
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(pady=(22, 0))
        self._add_text(row, "Don't have a MongoDB account?",
                       "body").pack(side="left", padx=(0, 6))
        link = self._add_text(row, "Create an account ↗", "link")
        link.configure(cursor="hand2")
        link.bind("<Button-1>",
                  lambda _event: webbrowser.open(MONGODB_SIGNUP_URL))
        link.pack(side="left")

    def _submit(self) -> None:
        self._error_label.pack_forget()
        password = self._password_entry.get()
        self._password_entry.delete(0, "end")
        self._submit_login(
            self._uri_entry.get(), self._username_entry.get(), password
        )

    def show_error(self, message: str) -> None:
        """Display a safe, readable login error above the Sign in button.

        Author: Archer (moved the label so it only takes space when shown)
        """
        self._error_label.configure(text=message)
        self._error_label.pack(anchor="w", pady=(0, 12),
                               before=self._sign_in_button)
