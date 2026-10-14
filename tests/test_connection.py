"""Tests for MongoDB connection lifecycle."""

import pytest

from db_gui.db import connection


class FakeAdmin:
    """Provide the ping command used by MongoConnection."""

    def command(self, name: str) -> None:
        assert name == "ping"


class FakeDatabase:
    """Record collection creation for a fake MongoDB database."""

    def __init__(self, name: str, databases: list[str], created: list[tuple[str, str]]) -> None:
        self.name = name
        self.databases = databases
        self.created = created

    def create_collection(self, name: str) -> None:
        self.created.append((self.name, name))
        self.databases.append(self.name)


class FakeClient:
    """Record client behavior without contacting MongoDB."""

    def __init__(self) -> None:
        self.admin = FakeAdmin()
        self.closed = False
        self.databases = ["zebra", "alpha"]
        self.created_collections: list[tuple[str, str]] = []

    def list_database_names(self) -> list[str]:
        return self.databases

    def __getitem__(self, name: str) -> FakeDatabase:
        return FakeDatabase(name, self.databases, self.created_collections)

    def close(self) -> None:
        self.closed = True


def test_connect_returns_sorted_database_names(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_client = FakeClient()
    monkeypatch.setattr(connection, "MongoClient",
                        lambda *args, **kwargs: fake_client)

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


def test_create_database_creates_initial_collection_and_returns_sorted_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = FakeClient()
    monkeypatch.setattr(connection, "MongoClient",
                        lambda *args, **kwargs: fake_client)
    service = connection.MongoConnection("mongodb://cluster.example")
    service.connect("alex", "secret")

    databases = service.create_database(" new_db ", " start_here ")

    assert fake_client.created_collections == [("new_db", "start_here")]
    assert databases == ["alpha", "new_db", "zebra"]


def test_create_database_rejects_existing_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = FakeClient()
    monkeypatch.setattr(connection, "MongoClient",
                        lambda *args, **kwargs: fake_client)
    service = connection.MongoConnection("mongodb://cluster.example")
    service.connect("alex", "secret")

    with pytest.raises(ValueError, match="already exists"):
        service.create_database("alpha", "start_here")

    assert fake_client.created_collections == []
