"""Callbacks the dashboard needs, bundled so the view stays under the
3-argument limit.

Author: Archer

The App fills these in (see gui/app.py `_show_dashboard`). The dashboard
widgets only ever call these; they never touch pymongo directly.
"""

from dataclasses import dataclass
from typing import Callable


@dataclass
class DashboardActions:
    """Everything the dashboard can ask the App to do."""

    # () -> list[DatabaseStats]
    load_databases: Callable
    # () -> ClusterStatus
    load_status: Callable
    # (database) -> list[str]
    list_collections: Callable
    # (database) -> None: open the collections screen
    open_database: Callable
    # (database, collection) -> None: open the documents screen
    open_collection: Callable
    # (database, first_collection) -> list[str]
    create_database: Callable
    # (database) -> None: runs the existing rename flow
    rename_database: Callable
    # () -> None: close the connection and go back to login
    disconnect: Callable
