"""Shared base for the app's styled pop-ups (FormDialog, MessageDialog).

Author: Archer

A ModalCard is a borderless window centered over the app with a 1px border,
a dimmed "scrim" behind it, and a modal grab so the app behind can't be
clicked until it closes. Subclasses build their content, then call
finish_setup().
"""

import tkinter as tk

import customtkinter as ctk

from ..theme import get_color

SCRIM_ALPHA = 0.6


class ModalCard(ctk.CTkToplevel):
    """Borderless, centered, modal pop-up over a dimmed app window."""

    WIDTH = 520

    def __init__(self, master) -> None:
        """Author: Archer"""
        super().__init__(master, fg_color=get_color("surface/card"))
        self._window = master.winfo_toplevel()
        self._focus_target = None  # widget to focus once shown
        self._scrim = _make_scrim(self._window)
        if self._scrim is not None:
            # Clicking the dimmed area must never cover the pop-up.
            self._scrim.bind("<Button-1>", lambda _event: self.lift())
        self.overrideredirect(True)  # the card draws its own title + ×
        # A Toplevel ignores border_width, so draw the 1px border with Tk's
        # highlight ring instead.
        border = get_color("border/default")
        self.configure(highlightthickness=1, highlightbackground=border,
                       highlightcolor=border)

    def finish_setup(self, focus_target=None) -> None:
        """Center over the app and go modal. Call after building content.

        Author: Archer
        """
        self._focus_target = focus_target
        self.update_idletasks()
        height = self.winfo_reqheight()
        x = self._window.winfo_rootx() + (self._window.winfo_width()
                                          - self.WIDTH) // 2
        y = self._window.winfo_rooty() + (self._window.winfo_height()
                                          - height) // 2
        self.geometry(f"{self.WIDTH}x{height}+{max(x, 0)}+{max(y, 0)}")
        # grab_set fails until the window is actually shown, so wait a bit.
        self.after(100, self._make_modal)

    def _make_modal(self) -> None:
        """Block clicks behind the pop-up and focus the chosen widget.

        Author: Archer
        """
        if not self.winfo_exists():
            return
        self.lift()
        try:
            self.grab_set()
        except tk.TclError:
            pass  # another window already holds the grab; still usable
        (self._focus_target or self).focus_set()

    def close(self) -> None:
        """Remove the pop-up and its dimmed backdrop.

        Author: Archer
        """
        if self._scrim is not None and self._scrim.winfo_exists():
            self._scrim.destroy()
        if self.winfo_exists():
            self.destroy()


def _make_scrim(window) -> tk.Toplevel | None:
    """A borderless, see-through dark window over `window` to dim it.

    Returns None where the platform doesn't support transparency.

    Author: Archer
    """
    window.update_idletasks()
    scrim = tk.Toplevel(window, background=get_color("overlay/scrim"))
    scrim.overrideredirect(True)
    scrim.geometry(f"{window.winfo_width()}x{window.winfo_height()}"
                   f"+{window.winfo_rootx()}+{window.winfo_rooty()}")
    try:
        scrim.attributes("-alpha", SCRIM_ALPHA)
    except tk.TclError:
        scrim.destroy()
        return None
    return scrim
