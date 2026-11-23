"""Tests for the login view (needs a display, skipped without one).

Author: Archer
"""

import pytest

tk = pytest.importorskip("tkinter")

from db_gui.gui.views.connection_view import ConnectionView  # noqa: E402
from db_gui.utils.saved_clusters import SavedCluster  # noqa: E402


@pytest.fixture
def root():
    try:
        window = tk.Tk()
    except tk.TclError:
        pytest.skip("No display available for Tk")
    window.withdraw()
    yield window
    window.destroy()


def make_view(root, saved=None):
    """Make a ConnectionView that records what Sign in sends."""
    calls = []
    view = ConnectionView(
        root, lambda entry, remember: calls.append((entry, remember)), saved)
    return view, calls


def fill_form(view, name: str = "") -> None:
    view._uri_entry.insert(0, "cluster0.example.net")
    view._username_entry.insert(0, "admin")
    view._password_entry.insert(0, "secret")
    if name:
        view._name_entry.insert(0, name)


def test_submit_sends_remember_true_by_default(root) -> None:
    view, calls = make_view(root)
    fill_form(view, "Work")

    view._submit()

    assert calls == [(SavedCluster(
        "cluster0.example.net", "admin", "secret", "Work"), True)]


def test_submit_sends_remember_false_when_unchecked(root) -> None:
    view, calls = make_view(root)
    fill_form(view)
    view._remember_me.deselect()

    view._submit()

    assert calls[0][1] is False


def test_update_name_field_hides_name_when_unchecked(root) -> None:
    view, _ = make_view(root)
    assert view._name_frame.winfo_manager() == "pack"

    view._remember_me.deselect()
    view._update_name_field()

    assert view._name_frame.winfo_manager() == ""


def test_fill_from_saved_copies_entry_into_form(root) -> None:
    saved = SavedCluster("c1.example.net", "u1", "p1", "Work")
    view, _ = make_view(root, [saved])

    view._fill_from_saved(saved.display_label())

    assert view._uri_entry.get() == "c1.example.net"
    assert view._username_entry.get() == "u1"
    assert view._password_entry.get() == "p1"
    assert view._name_entry.get() == "Work"


def test_saved_picker_only_shown_when_clusters_saved(root) -> None:
    view, _ = make_view(root)

    assert not hasattr(view, "_saved_picker")
