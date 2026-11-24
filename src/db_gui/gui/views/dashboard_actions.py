"""Callbacks the cluster pages (Dashboard, Collections) need, bundled so the
views stay under the 3-argument limit.

Author: Archer (added the Collections page callbacks)

The App fills these in (see gui/app.py `_make_actions`). The pages and their
widgets only ever call these; they never touch pymongo directly.
"""

from dataclasses import dataclass
from typing import Callable


@dataclass
class DashboardActions:
    """Everything a cluster page can ask the App to do."""

    # --- loading (called on a background thread) ---
    # () -> list[DatabaseStats]
    load_databases: Callable
    # () -> list[str]: database names only (fast; for the sidebar)
    list_database_names: Callable
    # (database) -> DatabaseStats
    load_database_stats: Callable
    # (database) -> list[CollectionStats]
    load_collection_stats: Callable
    # () -> ClusterStatus
    load_status: Callable
    # (database) -> list[str]
    list_collections: Callable
    # --- navigation ---
    # () -> None: back to the dashboard
    go_home: Callable
    # (database) -> None: open the Collections page
    open_database: Callable
    # (database, collection) -> None: open the documents screen
    open_collection: Callable
    # () -> None: close the connection and go back to login
    disconnect: Callable
    # --- features ---
    # (database, first_collection) -> list[str]
    create_database: Callable
    # (database) -> None: runs the existing rename flow
    rename_database: Callable
    # (database, collection) -> list[str]
    create_collection: Callable
    # (database, old_name, new_name) -> None
    rename_collection: Callable
