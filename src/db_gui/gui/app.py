"""Root application window and view routing."""

import customtkinter as ctk
from pymongo.errors import PyMongoError

from ..db.connection import MongoConnection
from .views.connection_view import ConnectionView
from .views.database_view import DatabaseView


class App(ctk.CTk):
    """The main window for the cluster login and database home views."""

    def __init__(self) -> None:
        super().__init__()

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.title("Database GUI Manager")
        self.geometry("900x600")
        self.minsize(600, 400)
        self._connection: MongoConnection | None = None
        self._current_view = None

        self._build_layout()

    def _build_layout(self) -> None:
        self._show_view(
            ConnectionView(self, self._connect_to_cluster)
        )

    def _show_view(self, view) -> None:
        if self._current_view is not None:
            self._current_view.destroy()
        self._current_view = view
        view.pack(expand=True, fill="both")

    def _connect_to_cluster(self, uri: str, username: str, password: str) -> None:
        try:
            connection = MongoConnection(uri)
            databases = connection.connect(username, password)
        except ValueError as error:
            self._current_view.show_error(str(error))
        except PyMongoError:
            self._current_view.show_error(
                "Login failed. Check the cluster URI, username, and password."
            )
        else:
            self._connection = connection
            self._show_view(DatabaseView(self, databases, self._disconnect))

    def _disconnect(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None
        self._show_view(ConnectionView(self, self._connect_to_cluster))


if __name__ == "__main__":
    # Lets you run this file directly (python src/db_gui/gui/app.py)
    # for quick UI iteration without going through main.py.
    App().mainloop()
