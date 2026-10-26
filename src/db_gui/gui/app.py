"""Root application window and view routing.

Author: Archer (bumped default window size for the restyled login view;
added the brand mark as the window icon)
"""

import customtkinter as ctk
from pymongo.errors import PyMongoError

from ..db.connection import MongoConnection
from .assets import BRAND_MARK, load_image
from .views.connection_view import ConnectionView
from .views.database_view import DatabaseView


class App(ctk.CTk):
    """The main window for the cluster login and database home views."""

    def __init__(self) -> None:
        super().__init__()

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.title("Arrow_>")
        self._set_window_icon()
        # Tall enough for the login card (design/Login.png) without clipping.
        self.geometry("1100x820")
        self.minsize(600, 400)
        self._connection: MongoConnection | None = None
        self._current_view = None

        self._build_layout()

    def _set_window_icon(self) -> None:
        """Show the brand mark in the title bar (and taskbar) next to the title.

        Author: Archer
        """
        # Kept on self: Tk drops the icon if the image is garbage-collected.
        self._window_icon = load_image(BRAND_MARK, self)
        self.iconphoto(True, self._window_icon)
        # On Windows, CTk swaps in its own logo ~200ms after startup unless
        # iconbitmap() was called. This flag is what iconbitmap() would set,
        # so it stops CTk from overwriting our icon.
        self._iconbitmap_method_called = True

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
            self._show_view(
                DatabaseView(
                    self,
                    databases,
                    self._create_database,
                    self._disconnect,
                )
            )

    def _create_database(
        self, database_name: str, collection_name: str
    ) -> list[str]:
        if self._connection is None:
            raise ValueError(
                "Connect to a cluster before creating a database.")
        return self._connection.create_database(database_name, collection_name)

    def _disconnect(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None
        self._show_view(ConnectionView(self, self._connect_to_cluster))


if __name__ == "__main__":
    # Lets you run this file directly (python src/db_gui/gui/app.py)
    # for quick UI iteration without going through main.py.
    App().mainloop()
