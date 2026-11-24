"""Shared text styles + a label factory for the dashboard widgets.

Author: Archer

Each style is (palette color key, pixel size, weight), so every dashboard
label picks its look by name and switching palettes restyles them all.
"""

import customtkinter as ctk

from ..theme import get_color, get_font

TEXT_STYLES = {
    "brand": ("text/primary", 20, "bold"),
    "title": ("text/primary", 28, "bold"),
    "dialog-title": ("text/primary", 20, "bold"),
    "label": ("text/primary", 12, "bold"),
    "subtitle": ("text/secondary", 13, "normal"),
    "section": ("text/muted", 11, "bold"),
    "body": ("text/primary", 13, "normal"),
    "body-bold": ("text/primary", 13, "bold"),
    "secondary": ("text/secondary", 12, "normal"),
    "muted": ("text/muted", 11, "normal"),
    "stat": ("text/primary", 24, "normal"),
    "link": ("accent/primary", 13, "normal"),
    "column": ("text/secondary", 11, "normal"),
    "error": ("feedback/danger", 12, "normal"),
}


def make_label(parent, text: str, style: str) -> ctk.CTkLabel:
    """Create a label in one of TEXT_STYLES (caller packs/grids it).

    Author: Archer
    """
    color_key, size, weight = TEXT_STYLES[style]
    return ctk.CTkLabel(parent, text=text, font=get_font(size, weight),
                        text_color=get_color(color_key), height=0, anchor="w")


def make_button(parent, text: str, command=None) -> ctk.CTkButton:
    """Create a flat secondary button; command=None makes it disabled.

    Disabled buttons keep their normal colors on purpose (not grayed out),
    so placeholders for future features look finished. Flip them on later
    by passing a command.

    Author: Archer
    """
    button = ctk.CTkButton(
        parent, text=text, height=34, corner_radius=6, font=get_font(13, "bold"),
        fg_color=get_color("button/secondary-fill"),
        hover_color=get_color("state/hover"), border_width=1,
        border_color=get_color("border/default"),
        text_color=get_color("text/primary"),
        text_color_disabled=get_color("text/primary"), command=command,
    )
    if command is None:
        button.configure(state="disabled")
    return button
