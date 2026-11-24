"""Root application window and view routing.

Author: Archer (bumped default window size for the restyled login view;
added the brand mark as the window icon; save remembered clusters to the
local JSON file after a successful login; swapped the database home screen
for the new DashboardView; rename now uses the styled FormDialog pop-up;
all native messagebox prompts replaced with in-app MessageDialog pop-ups;
databases now open the styled CollectionsView)
"""

from functools import partial

import customtkinter as ctk
from pymongo.errors import PyMongoError

from ..db.connection import MongoConnection
from ..utils.saved_clusters import (SavedCluster, load_saved_clusters,
                                    save_cluster)
from .assets import BRAND_MARK, load_image
from .views.connection_view import ConnectionView
from .views.dashboard_actions import DashboardActions
from .views.dashboard_view import DashboardView
from .views.collections_view import CollectionsView
from .views.document_view import DocumentActions, DocumentView
from .widgets.form_dialog import FormDialog, FormField, FormSpec
from .widgets.message_dialog import MessageSpec, show_dialog


class App(ctk.CTk):
    """The main window for the cluster login and database home views."""

    def __init__(self) -> None:
        super().__init__()

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.title("Arrow_>")
        self._set_window_icon()
        # Tall enough for the login card (design/Login.png) plus the
        # saved-cluster picker and cluster-name box without clipping.
        # Wide enough for the dashboard table (design/Dashboard.png).
        self.geometry("1280x940")
        self.minsize(600, 400)
        self._connection: MongoConnection | None = None
        # The login that's currently connected (names shown on the dashboard).
        self._login: SavedCluster | None = None
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
        self._show_login()

    def _show_login(self) -> None:
        """Show the login screen with the latest saved clusters.

        Author: Archer
        """
        self._show_view(ConnectionView(
            self, self._connect_to_cluster, load_saved_clusters()))

    def _show_view(self, view) -> None:
        if self._current_view is not None:
            self._current_view.destroy()
        self._current_view = view
        view.pack(expand=True, fill="both")

    def _connect_to_cluster(self, entry: SavedCluster, remember: bool) -> None:
        """Try the login; on success, save it (if remember) and go on.

        Author: Archer (takes a SavedCluster + remember-me flag)
        """
        try:
            connection = MongoConnection(entry.cluster)
            connection.connect(entry.username, entry.password)
        except ValueError as error:
            self._current_view.show_error(str(error))
        except PyMongoError:
            self._current_view.show_error(
                "Login failed. Check the cluster URI, username, and password."
            )
        else:
            self._connection = connection
            self._login = entry
            # Only remember logins that worked, and only when asked to.
            if remember:
                self._remember_cluster(entry)
            self._show_dashboard()

    def _remember_cluster(self, entry: SavedCluster) -> None:
        """Save the login to the local JSON file; warn (but carry on) if
        the file can't be written.

        Author: Archer
        """
        try:
            save_cluster(entry)
        except ValueError as error:
            show_dialog(self, MessageSpec("Cluster not saved", str(error),
                                          "warning"))
            
    def _make_actions(self) -> DashboardActions:
        """Everything the cluster pages can ask for, bound to this connection.

        Author: Archer
        """
        connection = self._connection
        return DashboardActions(
            load_databases=connection.list_database_stats,
            list_database_names=connection.list_databases,
            load_database_stats=connection.get_database_stats,
            load_collection_stats=connection.list_collection_stats,
            load_status=connection.get_cluster_status,
            list_collections=connection.list_collections,
            go_home=self._show_dashboard,
            open_database=self._collections_view,
            open_collection=self._documents_view,
            disconnect=self._disconnect,
            create_database=self._create_database,
            rename_database=self._rename_database,
            create_collection=connection.create_collection,
            rename_collection=connection.rename_collection,
        )

    def _show_dashboard(self) -> None:
        """Show the dashboard for the current connection.

        Author: Archer
        """
        self._show_view(DashboardView(self, self._login, self._make_actions()))

    def _collections_view(self, database: str) -> None:
        """Show the Collections page for one database.

        Author: Archer (styled CollectionsView replaces CollectionView)
        """
        self._show_view(CollectionsView(
            self, self._login, (self._make_actions(), database)))

    def _documents_view(self, database: str, collection: str) -> None:
        """Open the screen for one collection."""
        # partial fills in the database and collection names for the view
        actions = DocumentActions(
            back=lambda: self._collections_view(database),
            list_documents=partial(
                self._connection.list_documents, database, collection),
            add_document=partial(
                self._connection.add_document, database, collection),
            add_documents=partial(
                self._connection.add_documents, database, collection),
        )
        self._show_view(
            DocumentView(self, f"{database}.{collection}", actions))

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
        self._login = None
        self._show_login()

    def _rename_database(self, source_name: str) -> None:
        target_name = self._prompt_database_name(source_name)
        if target_name is None:
            return
        connection = self._connection
        if connection is None:
            show_dialog(self, MessageSpec(
                "Not connected", "Connect to a cluster before renaming.",
                "error"))
            return
        if not self._confirm_database_rename(connection, source_name, target_name):
            return
        try:
            archive_path = connection.rename_database(source_name, target_name)
        except (ValueError, PyMongoError, RuntimeError, OSError) as error:
            self._report_rename_failure(connection, error)
            return
        self._report_rename_success(
            connection, source_name, target_name, archive_path
        )

    def _prompt_database_name(self, source_name: str) -> str | None:
        """Ask for the new name in the Rename database pop-up
        (design/Rename database — pop-up.png). None = cancelled.

        Author: Archer (styled pop-up replaces CTkInputDialog; empty and
        unchanged names are caught inside the pop-up)
        """
        spec = FormSpec(
            title="Rename database",
            subtitle="Enter a new name for this database.",
            submit_text="Rename",
            fields=[FormField("New database name", "",
                              "Choose a unique name for this connection.",
                              initial=source_name)])
        dialog = FormDialog(self, spec, lambda values: (
            "Choose a different name." if values[0] == source_name else None))
        values = dialog.wait_for_values()
        return values[0] if values else None

    def _confirm_database_rename(
        self,
        connection: MongoConnection,
        source_name: str,
        target_name: str,
    ) -> bool:
        """Styled Yes/No confirm (design/Rename confirm popups.png).

        Author: Archer (in-app pop-up replaces messagebox.askyesno; the
        first line of the warning becomes the bold heading)
        """
        estimate = connection.get_database_size(source_name)
        warning = self._build_rename_warning(source_name, target_name, estimate)
        heading, _, details = warning.partition("\n\n")
        return show_dialog(self, MessageSpec(
            "Confirm database rename", details, "question", heading))

    def _report_rename_failure(
        self, connection: MongoConnection, error: Exception
    ) -> None:
        show_dialog(self, MessageSpec(
            "Database rename failed",
            f"{error}\n\nCheck the cluster state before retrying. If the "
            "message includes a local recovery archive path, keep that file.",
            "error"))
        # The dashboard shows its own error if the cluster can't be read.
        self._show_dashboard()

    def _report_rename_success(
        self,
        connection: MongoConnection,
        source_name: str,
        target_name: str,
        archive_path: str | None,
    ) -> None:
        self._show_dashboard()
        self._show_rename_outcome(source_name, target_name, archive_path)

    def _show_rename_outcome(
        self, source_name: str, target_name: str, archive_path: str | None
    ) -> None:
        """Styled result pop-up (design/Rename confirm popups.png).

        Author: Archer (in-app pop-up replaces messagebox)
        """
        if archive_path is None:
            show_dialog(self, MessageSpec(
                "Database renamed",
                f"'{source_name}' was saved to a local BSON archive, verified, "
                f"and restored as '{target_name}'. The original was removed."))
        else:
            show_dialog(self, MessageSpec(
                "Database renamed; local cleanup needed",
                f"'{source_name}' was restored as '{target_name}', but the "
                f"temporary local archive could not be removed:\n{archive_path}",
                "warning"))

    @staticmethod
    def _build_rename_warning(
        source_name: str, target_name: str, estimate: int | None
    ) -> str:
        if estimate is None:
            size_note = "We couldn't estimate how much local disk space is needed."
        else:
            size_mb = estimate / 1_000_000
            size_note = f"The database is about {size_mb:.1f} MB."
        return (
            f"Rename '{source_name}' to '{target_name}'?\n\n"
            "We'll save a temporary BSON archive on this computer and verify "
            "it before removing the old database. Then we'll create the new "
            "database, restore from the archive, and verify the restored data.\n\n"
            f"{size_note} The archive needs local disk space. It is removed "
            "after a successful rename; if automatic recovery fails, the "
            "archive is kept and its location is shown. This avoids keeping "
            "two database copies in the cluster at once. Your provider may "
            "not immediately reduce its reported allocated storage afterward.\n\n"
            "The local archive is not encrypted. Pause apps that are changing "
            "this database until the rename is finished."
        )

if __name__ == "__main__":
    # Lets you run this file directly (python src/db_gui/gui/app.py)
    # for quick UI iteration without going through main.py.
    App().mainloop()
