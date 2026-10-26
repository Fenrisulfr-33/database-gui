"""Color palettes and fonts shared by every view.

Author: Archer

Color keys mirror the "Arrow colors" variable names in design/Color palette.png
(e.g. "background/login", "accent/primary"), so a name in the design file maps
1:1 to a key here.

How palettes work:
- PALETTES holds every palette, keyed by palette name.
- A value is either a hex color ("#84d5a4") or the name of another key in the
  same palette ("accent/primary"). The second form is an alias: the textbox,
  button, and state colors point at base colors so changing one base color
  updates everything that uses it.
- Views should only ever call get_color("some/key"). They never hard-code hex.

Adding a new palette later: copy "arrow_dark", give it a new name, change the
hex values, then call set_palette("<new name>") (e.g. from a future settings
screen) before building the views.
"""

import tkinter.font as tkfont

import customtkinter as ctk

DEFAULT_PALETTE = "arrow_dark"

PALETTES: dict[str, dict[str, str]] = {
    "arrow_dark": {
        # Backgrounds & surfaces
        "background/app": "#141718",
        "background/login": "#191919",
        "background/editor": "#161a1b",
        "surface/chrome": "#191d1e",
        "surface/card": "#1d2223",
        "surface/login-card": "#1f1f1f",
        "surface/raised": "#242a2b",
        # Text
        "text/primary": "#e8edec",
        "text/secondary": "#99a5a2",
        "text/muted": "#697672",
        "text/field-key": "#b7cfd1",
        "text/disabled": "#4a5568",
        # Borders
        "border/default": "#303738",
        "border/subtle": "#1e2425",
        # Text box
        "textbox/fill-login": "#404040",
        "textbox/fill": "textbox/fill-login",
        "textbox/border": "border/default",
        "textbox/text": "text/primary",
        "textbox/placeholder": "text/secondary",
        "textbox/focus-ring": "accent/primary",
        # Buttons
        "button/fill": "accent/primary",
        # Not in the Figma palette yet: CustomTkinter needs a hover color.
        "button/fill-hover": "#6fc391",
        "button/text": "accent/on-primary",
        "button/secondary-fill": "surface/raised",
        "button/danger-fill": "feedback/danger",
        # Selection & states
        "state/selected": "#1f2d26",
        "state/selected-nav": "accent/subtle",
        "state/selected-text": "accent/primary",
        "state/highlight": "#202c26",
        "state/hover": "#232a2b",
        "state/disabled": "#202526",
        # Accent
        "accent/primary": "#84d5a4",
        "accent/on-primary": "#11271b",
        "accent/subtle": "#233c30",
        "accent/border": "#385543",
        "accent/surface": "#1a2520",
        "accent/divider": "#2a3d32",
        "accent/badge": "#1a2f22",
        # Feedback & overlay
        "feedback/danger": "#f28b82",
        "feedback/danger-subtle": "#3a2224",
        "feedback/warning": "#e5c07b",
        "feedback/warning-subtle": "#3a3222",
        "feedback/info": "#8ab4f8",
        "feedback/info-subtle": "#1f2a3a",
        "overlay/scrim": "#0c0e0e",
    },
}

# Monospace families in order of preference; the first one installed wins.
MONO_FONT_FAMILIES = (
    "JetBrains Mono", "Geist Mono", "Cascadia Mono", "Consolas",
    "Menlo", "DejaVu Sans Mono", "Courier New",
)

# Aliases should never chain this deep; the limit just stops a typo loop.
_MAX_ALIAS_DEPTH = 10

_state = {"palette": DEFAULT_PALETTE, "font_family": None}


def get_palette_names() -> list[str]:
    """Return every palette name (for a future settings dropdown).

    Author: Archer
    """
    return sorted(PALETTES)


def get_active_palette_name() -> str:
    """Return the name of the palette views are currently built with.

    Author: Archer
    """
    return _state["palette"]


def set_palette(palette_name: str) -> None:
    """Switch the active palette. Views built afterwards use the new colors.

    Author: Archer
    """
    if palette_name not in PALETTES:
        raise ValueError(f"Unknown palette: {palette_name}")
    _state["palette"] = palette_name


def get_color(key: str, palette_name: str | None = None) -> str:
    """Return the hex color for a key, following aliases to a real color.

    Author: Archer
    """
    palette = PALETTES[palette_name or _state["palette"]]
    value = key
    for _ in range(_MAX_ALIAS_DEPTH):
        if value not in palette:
            raise KeyError(f"Unknown color key: {value}")
        value = palette[value]
        if value.startswith("#"):
            return value
    raise ValueError(f"Color alias loop starting at: {key}")


def get_font(size: int, weight: str = "normal") -> ctk.CTkFont:
    """Return the app's monospace font at a pixel size ("normal"/"bold").

    Needs a Tk root window to exist, since it checks installed fonts.

    Author: Archer
    """
    if _state["font_family"] is None:
        installed = set(tkfont.families())
        _state["font_family"] = next(
            (name for name in MONO_FONT_FAMILIES if name in installed),
            "Courier",
        )
    return ctk.CTkFont(family=_state["font_family"], size=size, weight=weight)
