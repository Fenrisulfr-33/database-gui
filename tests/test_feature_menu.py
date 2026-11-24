"""Tests for the "···" feature menu (needs a display, skipped without one).

Author: Archer
"""

import pytest

tk = pytest.importorskip("tkinter")

from db_gui.gui.widgets.feature_menu import FeatureMenu, MenuItem  # noqa: E402


@pytest.fixture
def root():
    try:
        window = tk.Tk()
    except tk.TclError:
        pytest.skip("No display available for Tk")
    window.geometry("400x300")
    yield window
    window.destroy()


def make_menu(root, calls):
    anchor = tk.Button(root, text="···")
    anchor.pack()
    root.update()
    items = [MenuItem("Rename", "rename", lambda: calls.append("rename"))]
    return FeatureMenu(anchor, items)


def test_menu_lists_features_then_close(root) -> None:
    menu = make_menu(root, [])

    labels = [row.winfo_children()[1].cget("text") for row in menu.rows]

    assert labels == ["Rename", "Close"]
    menu.close()


def test_run_closes_menu_then_runs_feature(root) -> None:
    calls = []
    menu = make_menu(root, calls)

    menu._run(lambda: calls.append("rename"))

    assert calls == ["rename"]
    assert not menu.winfo_exists()


def test_highlight_turns_row_green_and_back(root) -> None:
    from db_gui.gui.theme import get_color
    menu = make_menu(root, [])
    row = menu.rows[0]

    menu._highlight(row, True)
    assert row.icon.cget("background") == get_color("accent/subtle")
    menu._highlight(row, False)
    assert row.icon.cget("background") == get_color("surface/card")
    menu.close()


def test_click_outside_closes_menu(root) -> None:
    menu = make_menu(root, [])
    root.update()

    class Click:
        x_root = menu.winfo_rootx() - 50
        y_root = menu.winfo_rooty() - 50

    menu._close_if_outside(Click())

    assert not menu.winfo_exists()
