"""Tests for the in-app message pop-up (needs a display, skipped without one).

Author: Archer
"""

import pytest

tk = pytest.importorskip("tkinter")

from db_gui.gui.widgets.message_dialog import (  # noqa: E402
    MessageDialog, MessageSpec)


@pytest.fixture
def root():
    try:
        window = tk.Tk()
    except tk.TclError:
        pytest.skip("No display available for Tk")
    window.geometry("700x500")
    yield window
    window.destroy()


def button_texts(dialog) -> list[str]:
    """Bottom-row button labels, primary (green) first."""
    return [button.cget("text") for button in dialog.buttons]


def test_question_has_yes_and_no_and_heading(root) -> None:
    dialog = MessageDialog(root, MessageSpec(
        "Confirm database rename", "Details", "question", "Rename 'a' to 'b'?"))

    assert button_texts(dialog) == ["Yes", "No"]
    dialog.close()


def test_info_has_only_ok(root) -> None:
    dialog = MessageDialog(root, MessageSpec("Database renamed", "Done."))

    assert button_texts(dialog) == ["OK"]
    dialog.close()


def test_finish_records_result_and_closes(root) -> None:
    dialog = MessageDialog(root, MessageSpec("Q", "?", "question"))

    dialog._finish(True)

    assert dialog.result is True
    assert not dialog.winfo_exists()


def test_closing_without_answer_means_no(root) -> None:
    dialog = MessageDialog(root, MessageSpec("Q", "?", "question"))

    dialog._finish(False)

    assert dialog.result is False
