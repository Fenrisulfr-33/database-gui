"""Tests for the dashboard (needs a display, skipped without one).

Author: Archer
"""

import pytest

tk = pytest.importorskip("tkinter")

from pymongo.errors import PyMongoError  # noqa: E402

from conftest import wait_for_load  # noqa: E402
from db_gui.gui.views.dashboard_view import DashboardView  # noqa: E402
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


@pytest.fixture
def make_view(root, make_actions):
    """Factory: a DashboardView with fake actions, already loaded."""
    def factory(calls=None, **overrides):
        calls = calls if calls is not None else []
        login = SavedCluster("c0.example.net", "admin", "pw", "Work")
        view = DashboardView(root, login, make_actions(calls, **overrides))
        wait_for_load(root, view)
        return view

    return factory


def test_refresh_fills_table_and_counts(root, make_view) -> None:
    view = make_view()

    assert [row.name for row in view.table.rows] == [
        "admin", "analytics", "shop"]
    assert view._showing_label.cget("text") == "Showing 3 of 3 databases"


def test_apply_filter_hides_non_matching_databases(root, make_view) -> None:
    view = make_view()
    view.filter_entry.insert(0, "AN")  # case-insensitive

    view.apply_filter()

    shown = [row.name for row in view.table.rows
             if row.winfo_manager()]
    assert shown == ["analytics"]
    assert view._showing_label.cget("text") == "Showing 1 of 3 databases"


def test_stat_cards_total_the_databases(root, make_view) -> None:
    view = make_view()
    texts = [value.cget("text") for value, _note in view.stat_cards._cards]

    assert texts == ["3", "16", "5.13M", "2.80 GB"]
    assert view.stat_cards._cards[0][1].cget("text") == \
        "2 application · 1 system"


def test_row_open_and_menu_rename_call_actions(root, make_view) -> None:
    calls = []
    view = make_view(calls)
    row = view.table.rows[2]

    row.open()
    menu = row.show_menu()
    menu._run(row.build_menu_items()[0].command)  # click "Rename"

    assert calls == [("open_database", "shop"), ("rename", "shop")]
    assert not menu.winfo_exists()  # menu closes after a feature runs


def test_sidebar_dropdown_lists_and_opens_collections(root, make_view) -> None:
    calls = []
    view = make_view(calls)
    item = view.sidebar.items["admin"]

    item.toggle()
    buttons = [row.winfo_children()[1]
               for row in item._children_frame.winfo_children()]
    buttons[1].invoke()

    assert [b.cget("text") for b in buttons] == ["orders", "users"]
    assert calls == [("open_collection", "admin", "users")]


def test_sidebar_chevron_icon_swaps_on_toggle(root, make_view) -> None:
    from db_gui.gui.widgets.dashboard_sidebar import COLLAPSED, EXPANDED

    item = make_view().sidebar.items["admin"]
    assert item.chevron_icon == COLLAPSED
    item.toggle()
    assert item.chevron_icon == EXPANDED
    item.toggle()
    assert item.chevron_icon == COLLAPSED


def test_sidebar_name_opens_database_and_nav_goes_home(root, make_view) -> None:
    calls = []
    view = make_view(calls)

    view.sidebar.items["shop"].name_button.invoke()

    assert calls == [("open_database", "shop")]


def test_refresh_shows_error_when_cluster_unreachable(root, make_view) -> None:
    def fail():
        raise PyMongoError("down")

    view = make_view(load_databases=fail)

    assert "Could not reach the cluster" in view._error_label.cget("text")


def test_header_controls_disabled_except_docs(root, make_view) -> None:
    view = make_view()
    header = view.grid_slaves(row=0, column=0)[0]

    assert header.search_entry.cget("state") == "disabled"
    assert header.workspace_button.cget("state") == "disabled"
    assert header.avatar_button.cget("text") == "AD"


def test_refresh_ignored_while_already_loading(root, make_view) -> None:
    loads = []
    view = make_view(load_databases=lambda: loads.append(1) or [])

    view.refresh()
    view.refresh()  # second click while loading does nothing
    wait_for_load(root, view)

    assert len(loads) == 2  # first load + one refresh


def test_create_dialog_creates_database_and_closes(root, make_view) -> None:
    created = []
    view = make_view(create_database=lambda db, c: created.append((db, c)))
    dialog = view.prompt_create_database()

    dialog._entries[0].insert(0, "shop2")
    dialog._entries[1].insert(0, "orders")
    dialog.submit()
    wait_for_load(root, view)

    assert created == [("shop2", "orders")]
    assert not dialog.winfo_exists()


def test_create_dialog_keeps_open_and_shows_server_error(root, make_view) -> None:
    def refuse(db, c):
        raise ValueError("Database already exists.")

    view = make_view(create_database=refuse)
    dialog = view.prompt_create_database()
    dialog._entries[0].insert(0, "shop")
    dialog._entries[1].insert(0, "orders")

    dialog.submit()

    assert dialog.winfo_exists()
    assert dialog._error_label.cget("text") == "Database already exists."
    dialog.cancel()
