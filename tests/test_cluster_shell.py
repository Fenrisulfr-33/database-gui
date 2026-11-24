"""Tests for the persistent cluster shell and the in-place sidebar
(needs a display, skipped without one).

Author: Archer
"""

import pytest

tk = pytest.importorskip("tkinter")

from conftest import make_shell, wait_for_load  # noqa: E402
from db_gui.gui.views.collections_view import CollectionsView  # noqa: E402
from db_gui.gui.views.dashboard_view import DashboardView  # noqa: E402


@pytest.fixture
def root():
    try:
        window = tk.Tk()
    except tk.TclError:
        pytest.skip("No display available for Tk")
    window.geometry("1280x900")
    yield window
    window.destroy()


def show(root, shell, make_page):
    """Show a page in the shell and wait for its data."""
    page = shell.show_page(make_page)
    wait_for_load(root, page)
    return page


def test_show_page_swaps_only_the_main_area(root, make_actions) -> None:
    shell = make_shell(root, make_actions([]))
    header, sidebar, status = shell.header, shell.sidebar, shell.status_bar
    dashboard = show(root, shell, DashboardView)
    items = dict(sidebar.items)

    collections = show(root, shell, lambda s: CollectionsView(s, "shop"))

    assert not dashboard.winfo_exists()  # old page destroyed
    assert shell.page is collections
    # Header, sidebar, status bar, and the sidebar's items all survive.
    assert (shell.header, shell.sidebar, shell.status_bar) == (
        header, sidebar, status)
    assert sidebar.items == items
    assert all(item.winfo_exists() for item in items.values())


def test_select_database_moves_the_highlight(root, make_actions) -> None:
    shell = make_shell(root, make_actions([]))
    show(root, shell, lambda s: CollectionsView(s, "shop"))
    shop = shell.sidebar.items["shop"]
    assert shop.is_expanded()

    show(root, shell, lambda s: CollectionsView(s, "admin"))

    admin = shell.sidebar.items["admin"]
    assert admin.is_expanded()
    assert admin.name_button.cget("fg_color") == admin.header.cget("fg_color")
    # shop lost its highlight and closed again (the highlight opened it).
    assert shop.name_button.cget("fg_color") == "transparent"
    assert not shop.is_expanded()


def test_unselect_keeps_dropdown_the_user_opened(root, make_actions) -> None:
    shell = make_shell(root, make_actions([]))
    show(root, shell, DashboardView)
    analytics = shell.sidebar.items["analytics"]
    analytics.toggle()  # the user opens it

    shell.sidebar.select_database("analytics")
    shell.sidebar.select_database(None)

    assert analytics.is_expanded()


def test_set_databases_adds_and_removes_only_changes(root, make_actions) -> None:
    shell = make_shell(root, make_actions([]))
    show(root, shell, DashboardView)
    sidebar = shell.sidebar
    admin = sidebar.items["admin"]

    sidebar.set_databases(["admin", "new_db", "shop"])

    assert list(sidebar.items) == ["admin", "new_db", "shop"]
    assert sidebar.items["admin"] is admin  # kept, not rebuilt
    assert sidebar._count_label.cget("text") == "3"


def test_reload_collections_rereads_one_database(root, make_actions) -> None:
    lists = {"shop": ["orders"]}
    actions = make_actions([], list_collections=lambda db: list(lists[db]))
    actions.list_database_names = lambda: ["shop"]
    shell = make_shell(root, actions)
    show(root, shell, lambda s: CollectionsView(s, "shop"))
    lists["shop"].append("returns")

    shell.sidebar.reload_collections("shop")

    item = shell.sidebar.items["shop"]
    buttons = [child.winfo_children()[1].cget("text")
               for child in item._children_frame.winfo_children()]
    assert buttons == ["orders", "returns"]


def test_create_collection_reloads_sidebar_collections(root, make_actions) -> None:
    shell = make_shell(root, make_actions([]))
    page = show(root, shell, lambda s: CollectionsView(s, "shop"))
    reloaded = []
    shell.sidebar.reload_collections = reloaded.append

    assert page._create_collection(["returns"]) is None

    assert reloaded == ["shop"]
    wait_for_load(root, page)
