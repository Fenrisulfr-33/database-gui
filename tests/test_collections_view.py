"""Tests for the Collections page (needs a display, skipped without one).

Author: Archer
"""

import pytest

tk = pytest.importorskip("tkinter")

from conftest import wait_for_load  # noqa: E402
from db_gui.gui.views.collections_view import CollectionsView  # noqa: E402
from db_gui.utils.saved_clusters import SavedCluster  # noqa: E402


@pytest.fixture
def root():
    try:
        window = tk.Tk()
    except tk.TclError:
        pytest.skip("No display available for Tk")
    window.geometry("1280x900")
    yield window
    window.destroy()


@pytest.fixture
def make_view(root, make_actions):
    """Factory: a CollectionsView for "shop" with fake actions, loaded."""
    def factory(calls=None, **overrides):
        calls = calls if calls is not None else []
        login = SavedCluster("c0.example.net", "admin", "pw", "Work")
        view = CollectionsView(
            root, login, (make_actions(calls, **overrides), "shop"))
        wait_for_load(root, view)
        return view

    return factory


def shown_names(view) -> list[str]:
    return [row.name for row in view.table.rows if row.winfo_manager()]


def test_table_lists_collections_a_to_z(root, make_view) -> None:
    view = make_view()

    assert shown_names(view) == ["customers", "orders", "payments"]
    assert view._tab_label.cget("text") == "Collections  3"
    assert view._showing_label.cget("text") == "Showing 3 of 3 collections"


def test_toggle_sort_flips_order_and_label(root, make_view) -> None:
    view = make_view()

    view.toggle_sort()

    assert shown_names(view) == ["payments", "orders", "customers"]
    assert "Z–A" in view.sort_button.cget("text")


def test_filter_survives_sorting(root, make_view) -> None:
    view = make_view()
    view.filter_entry.insert(0, "OR")
    view.apply_filter()

    view.toggle_sort()

    assert shown_names(view) == ["orders"]


def test_stat_cards_show_database_totals(root, make_view) -> None:
    view = make_view()
    texts = [value.cget("text") for value, _note in view.stat_cards._cards]

    assert texts == ["1,284,620", "842.6 MB", "1.12 GB", "25"]
    assert view.stat_cards._cards[1][1].cget("text") == \
        "671 B average document size"


def test_sidebar_highlights_and_expands_this_database(root, make_view) -> None:
    view = make_view()
    item = view.sidebar.items["shop"]

    assert item.is_expanded()
    assert item.name_button.cget("fg_color") == item.header.cget("fg_color")
    assert not view.sidebar.items["admin"].is_expanded()


def test_row_click_opens_documents(root, make_view) -> None:
    calls = []
    view = make_view(calls)

    view.table.rows[0].open()

    assert calls == [("open_collection", "shop", "customers")]


def test_rename_collection_dialog_renames_and_closes(root, make_view) -> None:
    calls = []
    view = make_view(calls)
    dialog = view.prompt_rename_collection("orders")
    dialog._entries[0].delete(0, "end")
    dialog._entries[0].insert(0, "sales")

    dialog.submit()
    wait_for_load(root, view)

    assert calls == [("rename_collection", "shop", "orders", "sales")]
    assert not dialog.winfo_exists()


def test_rename_collection_rejects_same_name(root, make_view) -> None:
    view = make_view()
    dialog = view.prompt_rename_collection("orders")  # prefilled "orders"

    dialog.submit()

    assert dialog._error_label.cget("text") == "Choose a different name."
    dialog.cancel()


def test_row_menu_offers_rename(root, make_view) -> None:
    view = make_view()

    items = view.table.rows[1].build_menu_items()

    assert [item.label for item in items] == ["Rename"]


def test_create_collection_dialog(root, make_view) -> None:
    calls = []
    view = make_view(calls)
    dialog = view.prompt_create_collection()
    dialog._entries[0].insert(0, "invoices")

    dialog.submit()
    wait_for_load(root, view)

    assert calls == [("create_collection", "shop", "invoices")]


def test_breadcrumb_and_nav_go_home(root, make_view) -> None:
    calls = []
    view = make_view(calls)

    view._actions.go_home()

    assert calls == [("go_home",)]
