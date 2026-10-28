"""Root application window and view routing."""

from tkinter import messagebox

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
            self._show_database_view(databases)

    def _show_database_view(self, databases: list[str]) -> None:
        self._show_view(
            DatabaseView(self, databases, self._rename_database, self._disconnect)
        )

    def _rename_database(self, source_name: str) -> None:
        target_name = self._prompt_database_name(source_name)
        if target_name is None:
            return
        connection = self._connection
        if connection is None:
            messagebox.showerror(
                "Not connected", "Connect to a cluster before renaming.", parent=self
            )
            return
        if not self._confirm_database_rename(connection, source_name, target_name):
            return
        try:
            marker_removed = connection.rename_database(source_name, target_name)
        except (ValueError, PyMongoError, RuntimeError) as error:
            self._report_rename_failure(connection, error)
            return
        self._report_rename_success(
            connection, source_name, target_name, marker_removed
        )

    def _prompt_database_name(self, source_name: str) -> str | None:
        dialog = ctk.CTkInputDialog(
            text=f"Enter a new name for '{source_name}':",
            title="Rename database",
        )
        target_name = dialog.get_input()
        if target_name is None:
            return None
        target_name = target_name.strip()
        if not target_name:
            messagebox.showerror(
                "Invalid name", "A database name is required.", parent=self
            )
            return None
        return target_name

    def _confirm_database_rename(
        self,
        connection: MongoConnection,
        source_name: str,
        target_name: str,
    ) -> bool:
        estimate = connection.get_database_size(source_name)
        warning = self._build_rename_warning(source_name, target_name, estimate)
        return messagebox.askyesno("Confirm database rename", warning, parent=self)

    def _report_rename_failure(
        self, connection: MongoConnection, error: Exception
    ) -> None:
        messagebox.showerror(
            "Database rename failed",
            f"{error}\n\nThe original database was not removed. If copying "
            "started, a marked partial destination may remain.",
            parent=self,
        )
        try:
            self._show_database_view(connection.list_databases())
        except PyMongoError:
            messagebox.showwarning(
                "Database list unavailable",
                "The database list could not be refreshed. Reconnect to "
                "check the cluster state.",
                parent=self,
            )

    def _report_rename_success(
        self,
        connection: MongoConnection,
        source_name: str,
        target_name: str,
        marker_removed: bool,
    ) -> None:
        try:
            self._show_database_view(connection.list_databases())
        except PyMongoError:
            messagebox.showwarning(
                "Database renamed",
                "The rename succeeded, but the database list could not be "
                "refreshed. Reconnect to see the updated list.",
                parent=self,
            )
            return
        self._show_rename_outcome(source_name, target_name, marker_removed)

    def _show_rename_outcome(
        self, source_name: str, target_name: str, marker_removed: bool
    ) -> None:
        if marker_removed:
            messagebox.showinfo(
                "Database renamed",
                f"'{source_name}' was copied to '{target_name}' and the original "
                "was removed.",
                parent=self,
            )
        else:
            messagebox.showwarning(
                "Database renamed; cleanup needed",
                f"'{source_name}' was removed after verification, but the "
                "temporary recovery marker remains in '{target_name}'.",
                parent=self,
            )

    @staticmethod
    def _build_rename_warning(
        source_name: str, target_name: str, estimate: int | None
    ) -> str:
        if estimate is None:
            size_note = "We couldn't estimate how much extra storage the copy needs."
        else:
            size_mb = estimate / 1_000_000
            size_note = f"The database is about {size_mb:.1f} MB."
        return (
            f"Rename '{source_name}' to '{target_name}'?\n\n"
            "We'll copy your database to the new name. Once the copy is "
            "complete, we'll remove the old one.\n\n"
            f"{size_note} The copy needs extra storage while it runs, and the "
            "actual amount available may be different. If there isn't enough "
            "space or the copy is interrupted, your original database will "
            "stay safe. An unfinished copy may need to be removed before "
            "trying again.\n\n"
            "Please pause apps that are changing this database until the "
            "rename is finished."
        )

    def _disconnect(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None
        self._show_view(ConnectionView(self, self._connect_to_cluster))


if __name__ == "__main__":
    # Lets you run this file directly (python src/db_gui/gui/app.py)
    # for quick UI iteration without going through main.py.
    App().mainloop()
