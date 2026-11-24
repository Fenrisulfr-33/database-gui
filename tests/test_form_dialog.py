"""Tests for the styled pop-up form (needs a display, skipped without one).

Author: Archer
"""

import pytest

tk = pytest.importorskip("tkinter")

from db_gui.gui.widgets.form_dialog import (  # noqa: E402
    FormDialog, FormField, FormSpec)


@pytest.fixture
def root():
    try:
        window = tk.Tk()
    except tk.TclError:
        pytest.skip("No display available for Tk")
    window.geometry("400x300")
    yield window
    window.destroy()


def make_dialog(root, on_submit=None, initial: str = "") -> FormDialog:
    spec = FormSpec("Rename database", "Enter a new name.", "Rename",
                    [FormField("New database name", "", "hint", initial)])
    return FormDialog(root, spec, on_submit)


def test_submit_closes_and_keeps_values(root) -> None:
    dialog = make_dialog(root, initial="  shop  ")

    dialog.submit()

    assert dialog.values == ["shop"]  # trimmed
    assert not dialog.winfo_exists()


def test_submit_requires_every_field(root) -> None:
    dialog = make_dialog(root)

    dialog.submit()

    assert dialog.winfo_exists()
    assert dialog._error_label.cget("text") == "New database name is required."
    dialog.cancel()


def test_submit_shows_error_from_on_submit(root) -> None:
    dialog = make_dialog(root, lambda values: "Choose a different name.",
                         initial="shop")

    dialog.submit()

    assert dialog.winfo_exists()
    assert dialog._error_label.cget("text") == "Choose a different name."
    dialog.cancel()


def test_cancel_returns_no_values_and_removes_scrim(root) -> None:
    dialog = make_dialog(root, initial="shop")
    scrim = dialog._scrim

    dialog.cancel()

    assert dialog.values is None
    assert scrim is None or not scrim.winfo_exists()
