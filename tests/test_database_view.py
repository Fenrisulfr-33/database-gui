"""Tests for database list actions."""

from db_gui.gui.views import database_view


def test_database_rows_offer_selection_and_rename(monkeypatch) -> None:
    buttons = []

    class FakeWidget:
        def __init__(self, *args, **kwargs) -> None:
            self.kwargs = kwargs

        def pack(self, **kwargs) -> None:
            pass

        def winfo_children(self) -> list:
            return []

        def destroy(self) -> None:
            pass

    monkeypatch.setattr(database_view.ctk, "CTkFrame", FakeWidget)
    monkeypatch.setattr(
        database_view.ctk,
        "CTkButton",
        lambda *args, **kwargs: buttons.append(FakeWidget(**kwargs))
        or buttons[-1],
    )
    view = object.__new__(database_view.DatabaseView)
    view._database_list = FakeWidget()
    selected = []
    renamed = []
    view._collections_callback = selected.append
    view._rename_database_callback = renamed.append

    view._populate_databases(["alpha"])

    assert [button.kwargs["text"] for button in buttons] == ["alpha", "Rename"]
    buttons[0].kwargs["command"]()
    buttons[1].kwargs["command"]()
    assert selected == ["alpha"]
    assert renamed == ["alpha"]
