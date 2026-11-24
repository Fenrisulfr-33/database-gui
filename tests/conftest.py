"""Shared fixtures for the cluster page tests (Dashboard, Collections).

Author: Archer
"""

import time

import pytest

from db_gui.db.connection import (ClusterStatus, CollectionStats,
                                  DatabaseStats)

DATABASES = [
    DatabaseStats("admin", 2, 48, 96_000, 192_000),
    DatabaseStats("analytics", 8, 3_842_100, 1_240_000_000, 1_680_000_000),
    DatabaseStats("shop", 6, 1_284_620, 842_600_000, 1_120_000_000,
                  indexes=25, index_size=79_600_000, average_document_size=671),
]
COLLECTIONS = [
    CollectionStats("orders", 428_520, 312_600_000, 6, 28_400_000, 42),
    CollectionStats("customers", 24_680, 18_400_000, 4, 2_800_000, 18),
    CollectionStats("payments", 14_000, 36_200_000, 4, 3_200_000, 16),
]


@pytest.fixture
def make_actions():
    """Factory: DashboardActions whose calls are recorded, not sent to Mongo.

    make_actions(calls, load_databases=..., create_database=..., ...) lets a
    test swap in any callback.
    """
    from db_gui.gui.views.dashboard_actions import DashboardActions

    def factory(calls: list, **overrides) -> DashboardActions:
        fields = dict(
            load_databases=lambda: list(DATABASES),
            list_database_names=lambda: [db.name for db in DATABASES],
            load_database_stats=lambda db: DATABASES[2],
            load_collection_stats=lambda db: list(COLLECTIONS),
            load_status=lambda: ClusterStatus("c0.example.net", 24,
                                              "7.0.14", "rs0"),
            list_collections=lambda db: ["orders", "users"],
            go_home=lambda: calls.append(("go_home",)),
            open_database=lambda db: calls.append(("open_database", db)),
            open_collection=lambda db, c: calls.append(
                ("open_collection", db, c)),
            disconnect=lambda: calls.append(("disconnect",)),
            create_database=lambda db, c: [],
            rename_database=lambda db: calls.append(("rename", db)),
            create_collection=lambda db, c: calls.append(
                ("create_collection", db, c)),
            rename_collection=lambda db, old, new: calls.append(
                ("rename_collection", db, old, new)),
        )
        fields.update(overrides)
        return DashboardActions(**fields)

    return factory


def wait_for_load(root, view) -> None:
    """Pump Tk events until a page's background load has finished."""
    deadline = time.monotonic() + 5
    while view.loading and time.monotonic() < deadline:
        root.update()
        time.sleep(0.01)
    assert not view.loading, "page load did not finish"
