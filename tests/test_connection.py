"""Tests for MongoDB connection lifecycle."""

import pytest
import mongomock

from db_gui.db import connection


class FakeAdmin:
    """Provide the ping command used by MongoConnection."""

    def command(self, name: str) -> None:
        assert name == "ping"


class FakeClient:
    """Record client behavior without contacting MongoDB."""

    def __init__(self) -> None:
        self.admin = FakeAdmin()
        self.closed = False

    def list_database_names(self) -> list[str]:
        return ["zebra", "alpha"]

    def close(self) -> None:
        self.closed = True


def _connected_service() -> tuple[connection.MongoConnection, mongomock.MongoClient]:
    client = mongomock.MongoClient()
    service = connection.MongoConnection("mongodb://cluster.example")
    service._client = client
    return service, client


def _add_collection_metadata(database, name: str) -> None:
    database.list_collections = lambda: iter(
        [{"name": name, "type": "collection", "options": {}}]
    )


def test_connect_returns_sorted_database_names(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_client = FakeClient()
    monkeypatch.setattr(connection, "MongoClient", lambda *args, **kwargs: fake_client)

    service = connection.MongoConnection("mongodb://cluster.example")

    assert service.connect("alex", "secret") == ["alpha", "zebra"]
    service.close()
    assert fake_client.closed


def test_reconnect_closes_previous_client(monkeypatch: pytest.MonkeyPatch) -> None:
    first_client = FakeClient()
    second_client = FakeClient()
    clients = iter([first_client, second_client])
    monkeypatch.setattr(
        connection,
        "MongoClient",
        lambda *args, **kwargs: next(clients),
    )

    service = connection.MongoConnection("mongodb://cluster.example")

    service.connect("alex", "secret")
    assert not first_client.closed

    service.connect("alex", "secret")

    assert first_client.closed
    assert not second_client.closed


def test_connect_rejects_missing_credentials() -> None:
    service = connection.MongoConnection("mongodb://cluster.example")

    with pytest.raises(ValueError, match="required"):
        service.connect("", "secret")


def test_connect_rejects_missing_uri() -> None:
    service = connection.MongoConnection("")

    with pytest.raises(ValueError, match="required"):
        service.connect("alex", "secret")


def test_rename_database_copies_data_and_indexes_before_dropping_source() -> None:
    service, client = _connected_service()
    source = client["misspelled"]
    source["records"].insert_many([{"value": 1}, {"value": 2}])
    source["records"].create_index("value")
    _add_collection_metadata(source, "records")
    client.get_database("renamed").list_collections = lambda: iter(
        [{"name": "records", "type": "collection"}]
    )

    marker_removed = service.rename_database("misspelled", "renamed")

    assert marker_removed
    assert "misspelled" not in client.list_database_names()
    assert list(client["renamed"]["records"].find({}, {"_id": 0})) == [
        {"value": 1},
        {"value": 2},
    ]
    assert "value_1" in client["renamed"]["records"].index_information()
    assert connection.MongoConnection._RENAME_STATE_COLLECTION not in (
        client["renamed"].list_collection_names()
    )


def test_rename_database_preserves_source_and_marks_partial_copy_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, client = _connected_service()
    source = client["misspelled"]
    source["records"].insert_one({"value": 1})
    _add_collection_metadata(source, "records")
    monkeypatch.setattr(
        source["records"], "find", lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("copy interrupted")
        )
    )

    with pytest.raises(RuntimeError, match="copy interrupted"):
        service.rename_database("misspelled", "renamed")

    assert "misspelled" in client.list_database_names()
    assert "renamed" in client.list_database_names()
    marker = client["renamed"][connection.MongoConnection._RENAME_STATE_COLLECTION]
    assert marker.find_one({"_id": "rename"})["status"] == "copying"


def test_rename_database_rejects_existing_destination() -> None:
    service, client = _connected_service()
    client["misspelled"]["records"].insert_one({"value": 1})
    client["renamed"]["records"].insert_one({"value": 2})

    with pytest.raises(ValueError, match="already exists"):
        service.rename_database("misspelled", "renamed")

    assert "misspelled" in client.list_database_names()
    assert client["renamed"]["records"].find_one()["value"] == 2


@pytest.mark.parametrize("target_name", ["", "has.dot", "has/slash", "too-long-" * 8])
def test_rename_database_rejects_invalid_name(target_name: str) -> None:
    service, _ = _connected_service()

    with pytest.raises(ValueError, match="valid|64 bytes"):
        service.rename_database("source", target_name)