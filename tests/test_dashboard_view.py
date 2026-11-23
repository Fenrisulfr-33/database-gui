"""Tests for the dashboard (needs a display, skipped without one).

Author: Archer
"""

import time

import pytest

tk = pytest.importorskip("tkinter")

from pymongo.errors import PyMongoError  # noqa: E402

from db_gui.db.connection import ClusterStatus, DatabaseStats  # noqa: E402
from db_gui.gui.views.dashboard_actions import DashboardActions  # noqa: E402
from db_gui.gui.views.dashboard_view import DashboardView  # noqa: E402
from db_gui.utils.saved_clusters import SavedCluster  # noqa: E402

DATABASES = [
    DatabaseStats("admin", 2, 48, 96_000, 192_000),
    DatabaseStats("analytics", 8, 3_842_100, 1_240_000_000, 1_680_000_000),
    DatabaseStats("shop", 6, 1_284_620, 842_600_000, 1_120_000_000),
]


@pytest.fixture
def root():
    try:
        window = tk.Tk()
    except tk.TclError:
        pytest.skip("No display available for Tk")
    window.withdraw()
    yield window
    window.destroy()


def wait_for_load(root, view) -> None:
    """Pump Tk events until the background stats load has finished."""
    deadline = time.monotonic() + 5
    while view.loading and time.monotonic() < deadline:
        root.update()
        time.sleep(0.01)
    assert not view.loading, "dashboard load did not finish"


def make_view(root, calls=None, load_databases=None, create=None):
    """A DashboardView whose actions record calls instead of hitting Mongo.

    Waits for the first background load so tests see the filled table.
    """
    calls = calls if calls is not None else []
    actions = DashboardActions(
        load_databases=load_databases or (lambda: list(DATABASES)),
        load_status=lambda: ClusterStatus("c0.example.net", 24, "7.0.14", "rs0"),
        list_collections=lambda db: ["orders", "users"],
        open_database=lambda db: calls.append(("open_database", db)),
        open_collection=lambda db, c: calls.append(("open_collection", db, c)),
        create_database=create or (lambda db, c: []),
        rename_database=lambda db: calls.append(("rename", db)),
        disconnect=lambda: calls.append(("disconnect",)),
    )
    login = SavedCluster("c0.example.net", "admin", "pw", "Work")
    view = DashboardView(root, login, actions)
    wait_for_load(root, view)
    return view


def test_refresh_fills_table_and_counts(root) -> None:
    view = make_view(root)

    assert [row.database for row in view.table._rows] == [
        "admin", "analytics", "shop"]
    assert view._showing_label.cget("text") == "Showing 3 of 3 databases"


def test_apply_filter_hides_non_matching_databases(root) -> None:
    view = make_view(root)
    view.filter_entry.insert(0, "AN")  # case-insensitive

    view.apply_filter()

    shown = [row.database for row in view.table._rows
             if row.winfo_manager()]
    assert shown == ["analytics"]
    assert view._showing_label.cget("text") == "Showing 1 of 3 databases"


def test_stat_cards_total_the_databases(root) -> None:
    view = make_view(root)
    texts = [value.cget("text") for value, _note in view.stat_cards._cards]

    assert texts == ["3", "16", "5.13M", "2.80 GB"]
    assert view.stat_cards._cards[0][1].cget("text") == \
        "2 application · 1 system"


def test_row_open_and_menu_rename_call_actions(root) -> None:
    calls = []
    view = make_view(root, calls)
    row = view.table._rows[2]

    row.open()
    menu = row.show_menu()
    menu._run(row.build_menu_items()[0].command)  # click "Rename"

    assert calls == [("open_database", "shop"), ("rename", "shop")]
    assert not menu.winfo_exists()  # menu closes after a feature runs


def test_sidebar_dropdown_lists_and_opens_collections(root) -> None:
    calls = []
    view = make_view(root, calls)
    item = view.sidebar._explorer.winfo_children()[0]

    item.toggle()
    buttons = item._children_frame.winfo_children()
    buttons[1].invoke()

    assert [b.cget("text") for b in buttons] == ["orders", "users"]
    assert calls == [("open_collection", "admin", "users")]


def test_refresh_shows_error_when_cluster_unreachable(root) -> None:
    def fail():
        raise PyMongoError("down")

    view = make_view(root, load_databases=fail)

    assert "Could not reach the cluster" in view._error_label.cget("text")


def test_header_controls_disabled_except_docs(root) -> None:
    view = make_view(root)
    header = view.grid_slaves(row=0, column=0)[0]

    assert header.search_entry.cget("state") == "disabled"
    assert header.workspace_button.cget("state") == "disabled"
    assert header.avatar_button.cget("text") == "AD"


def test_refresh_ignored_while_already_loading(root) -> None:
    loads = []
    view = make_view(root, load_databases=lambda: loads.append(1) or [])

    view.refresh()
    view.refresh()  # second click while loading does nothing
    wait_for_load(root, view)

    assert len(loads) == 2  # first load + one refresh


def test_create_dialog_creates_database_and_closes(root) -> None:
    created = []
    view = make_view(root, create=lambda db, c: created.append((db, c)))
    dialog = view.prompt_create_database()

    dialog._entries[0].insert(0, "shop2")
    dialog._entries[1].insert(0, "orders")
    dialog.submit()
    wait_for_load(root, view)

    assert created == [("shop2", "orders")]
    assert not dialog.winfo_exists()


def test_create_dialog_keeps_open_and_shows_server_error(root) -> None:
    def refuse(db, c):
        raise ValueError("Database already exists.")

    view = make_view(root, create=refuse)
    dialog = view.prompt_create_database()
    dialog._entries[0].insert(0, "shop")
    dialog._entries[1].insert(0, "orders")

    dialog.submit()

    assert dialog.winfo_exists()
    assert dialog._error_label.cget("text") == "Database already exists."
    dialog.cancel()
