"""Tests for utils/saved_clusters.py (the remember-me JSON file).

Author: Archer
"""

import json
from pathlib import Path

import pytest

from db_gui.utils import saved_clusters
from db_gui.utils.saved_clusters import SavedCluster


def test_load_saved_clusters_returns_empty_when_file_missing(
        tmp_path: Path) -> None:
    assert saved_clusters.load_saved_clusters(tmp_path / "none.json") == []


def test_load_saved_clusters_returns_empty_for_bad_json(tmp_path: Path) -> None:
    path = tmp_path / "saved.json"
    path.write_text("{not json", encoding="utf-8")

    assert saved_clusters.load_saved_clusters(path) == []


def test_load_saved_clusters_skips_malformed_entries(tmp_path: Path) -> None:
    path = tmp_path / "saved.json"
    path.write_text(json.dumps([
        {"cluster": "c1", "username": "u1", "password": "p1", "name": "Work"},
        {"cluster": "c2"},  # missing username/password
        "not a dict",
        {"cluster": "c3", "username": "u3", "password": "p3", "name": 5},
    ]), encoding="utf-8")

    assert saved_clusters.load_saved_clusters(path) == [
        SavedCluster("c1", "u1", "p1", "Work"),
        SavedCluster("c3", "u3", "p3", ""),
    ]


def test_save_cluster_creates_file_and_folder(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "saved.json"

    saved_clusters.save_cluster(SavedCluster("c1", "u1", "p1", "Work"), path)

    assert json.loads(path.read_text(encoding="utf-8")) == [
        {"cluster": "c1", "username": "u1", "password": "p1", "name": "Work"}
    ]


def test_save_cluster_appends_different_logins(tmp_path: Path) -> None:
    path = tmp_path / "saved.json"

    saved_clusters.save_cluster(SavedCluster("c1", "u1", "p1"), path)
    saved_clusters.save_cluster(SavedCluster("c1", "u2", "p2"), path)

    assert len(saved_clusters.load_saved_clusters(path)) == 2


def test_save_cluster_updates_same_login_and_keeps_old_name(
        tmp_path: Path) -> None:
    path = tmp_path / "saved.json"

    saved_clusters.save_cluster(SavedCluster("c1", "u1", "old", "Work"), path)
    saved_clusters.save_cluster(SavedCluster("c1", "u1", "new", ""), path)

    assert saved_clusters.load_saved_clusters(path) == [
        SavedCluster("c1", "u1", "new", "Work")
    ]


def test_save_cluster_raises_value_error_when_unwritable(
        tmp_path: Path) -> None:
    # A directory where the file should be makes the write fail.
    path = tmp_path / "saved.json"
    path.mkdir()

    with pytest.raises(ValueError, match="Could not save the cluster"):
        saved_clusters.save_cluster(SavedCluster("c1", "u1", "p1"), path)


def test_display_label_uses_name_or_falls_back_to_cluster() -> None:
    assert SavedCluster("c1", "u1", "p1", "Work").display_label() == "Work (u1)"
    assert SavedCluster("c1", "u1", "p1").display_label() == "c1 (u1)"
