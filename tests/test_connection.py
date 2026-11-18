"""Tests for MongoDB connection lifecycle."""

import pytest
import mongomock

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


def _connected_service() -> tuple[connection.MongoConnection, mongomock.MongoClient]:
    client = mongomock.MongoClient()
    get_database = client.get_database

    def database_with_collection_metadata(name: str):
        database = get_database(name)
        database.list_collections = lambda: iter(
            [
                {"name": collection, "type": "collection", "options": {}}
                for collection in database.list_collection_names()
            ]
        )
        return database

    client.get_database = database_with_collection_metadata
    service = connection.MongoConnection("mongodb://cluster.example")
    service._client = client
    return service, client


def _add_collection_metadata(database, name: str) -> None:
    database.list_collections = lambda: iter(
        [{"name": name, "type": "collection", "options": {}}]
    )


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


def test_rename_database_restores_data_and_indexes_from_local_archive() -> None:
    service, client = _connected_service()
    source = client["misspelled"]
    source["records"].insert_many([{"value": 1}, {"value": 2}])
    source["records"].create_index("value")
    _add_collection_metadata(source, "records")

    archive_path = service.rename_database("misspelled", "renamed")

    assert archive_path is None
    assert "misspelled" not in client.list_database_names()
    assert list(client["renamed"]["records"].find({}, {"_id": 0})) == [
        {"value": 1},
        {"value": 2},
    ]
    assert "value_1" in client["renamed"]["records"].index_information()


def test_rename_database_keeps_source_when_local_export_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, client = _connected_service()
    source = client["misspelled"]
    source["records"].insert_one({"value": 1})
    _add_collection_metadata(source, "records")

    def fail_find(query):
        assert query == {}
        raise RuntimeError("copy interrupted")

    monkeypatch.setattr(source["records"], "find", fail_find)

    with pytest.raises(RuntimeError, match="copy interrupted"):
        service.rename_database("misspelled", "renamed")

    assert "misspelled" in client.list_database_names()
    assert "renamed" not in client.list_database_names()


def test_rename_database_restores_source_if_new_database_restore_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, client = _connected_service()
    source = client["misspelled"]
    source["records"].insert_one({"value": 1})
    _add_collection_metadata(source, "records")
    restore_archive = connection.MongoConnection._restore_archive

    def fail_new_database(
        database, archive_path: str, created_content: list[str] | None = None
    ) -> None:
        if database.name == "renamed":
            raise RuntimeError("restore interrupted")
        restore_archive(database, archive_path, created_content)

    monkeypatch.setattr(
        connection.MongoConnection, "_restore_archive", staticmethod(fail_new_database)
    )

    with pytest.raises(RuntimeError, match="original database was restored"):
        service.rename_database("misspelled", "renamed")

    assert "misspelled" in client.list_database_names()
    assert "renamed" not in client.list_database_names()
    assert client["misspelled"]["records"].find_one()["value"] == 1


def test_rename_database_rejects_existing_destination() -> None:
    service, client = _connected_service()
    client["misspelled"]["records"].insert_one({"value": 1})
    client["renamed"]["records"].insert_one({"value": 2})

    with pytest.raises(ValueError, match="already exists"):
        service.rename_database("misspelled", "renamed")

    assert "misspelled" in client.list_database_names()
    assert client["renamed"]["records"].find_one()["value"] == 2


@pytest.mark.parametrize(
    "target_name", ["", "has.dot", "has/slash", "too-long-" * 8]
)
def test_rename_database_rejects_invalid_name(target_name: str) -> None:
    service, _ = _connected_service()

    with pytest.raises(ValueError, match="valid|64 bytes"):
        service.rename_database("source", target_name)


# documents

@pytest.fixture
def mongo_service(monkeypatch: pytest.MonkeyPatch) -> connection.MongoConnection:
    """A connected MongoConnection that uses mongomock."""
    fake_client = mongomock.MongoClient()
    monkeypatch.setattr(connection, "MongoClient",
                        lambda *args, **kwargs: fake_client)
    service = connection.MongoConnection("mongodb://cluster.example")
    service.connect("alex", "secret")
    return service


def test_list_documents_returns_empty_list_for_empty_collection(
    mongo_service: connection.MongoConnection,
) -> None:
    assert mongo_service.list_documents("shop", "items") == []


def test_list_documents_requires_connection() -> None:
    service = connection.MongoConnection("mongodb://cluster.example")

    with pytest.raises(ValueError, match="Connect to a MongoDB cluster"):
        service.list_documents("shop", "items")


def test_list_documents_is_capped_and_newest_first(
    mongo_service: connection.MongoConnection,
) -> None:
    for number in range(connection.DOCUMENT_LIST_LIMIT + 5):
        mongo_service.add_document("shop", "items", {"_id": number})

    documents = mongo_service.list_documents("shop", "items")

    assert len(documents) == connection.DOCUMENT_LIST_LIMIT
    assert documents[0]["_id"] == connection.DOCUMENT_LIST_LIMIT + 4


def test_add_document_inserts_and_returns_updated_list(
    mongo_service: connection.MongoConnection,
) -> None:
    documents = mongo_service.add_document("shop", "items", {"name": "pen"})

    assert [doc["name"] for doc in documents] == ["pen"]
    assert "_id" in documents[0]  # MongoDB assigned one


def test_add_document_allows_identical_content_with_different_id(
    mongo_service: connection.MongoConnection,
) -> None:
    mongo_service.add_document("shop", "items", {"_id": 1, "name": "pen"})

    documents = mongo_service.add_document(
        "shop", "items", {"_id": 2, "name": "pen"})

    assert len(documents) == 2


def test_add_document_allows_same_name_with_different_content(
    mongo_service: connection.MongoConnection,
) -> None:
    mongo_service.add_document("shop", "items", {"name": "pen", "color": "blue"})

    documents = mongo_service.add_document(
        "shop", "items", {"name": "pen", "color": "red"})

    assert len(documents) == 2


def test_add_document_new_document_appears_in_list_immediately(
    mongo_service: connection.MongoConnection,
) -> None:
    mongo_service.add_document("shop", "items", {"name": "pen"})

    documents = mongo_service.add_document("shop", "items", {"name": "ink"})

    assert {doc["name"] for doc in documents} == {"pen", "ink"}


def test_add_document_only_touches_the_given_collection(
    mongo_service: connection.MongoConnection,
) -> None:
    mongo_service.add_document("shop", "items", {"name": "pen"})

    assert mongo_service.list_documents("shop", "orders") == []
    assert mongo_service.list_documents("other_db", "items") == []


def test_add_document_rejects_duplicate_id(
    mongo_service: connection.MongoConnection,
) -> None:
    mongo_service.add_document("shop", "items", {"_id": 1})

    with pytest.raises(ValueError, match="already exists"):
        mongo_service.add_document("shop", "items", {"_id": 1})


def test_add_document_rejects_non_dict(
    mongo_service: connection.MongoConnection,
) -> None:
    with pytest.raises(ValueError, match="JSON object"):
        mongo_service.add_document("shop", "items", ["not", "a", "dict"])  # type: ignore[arg-type]


def test_add_document_requires_connection() -> None:
    service = connection.MongoConnection("mongodb://cluster.example")

    with pytest.raises(ValueError, match="Connect to a MongoDB cluster"):
        service.add_document("shop", "items", {"name": "pen"})


# importing many documents


def test_add_documents_inserts_all_and_returns_result(
    mongo_service: connection.MongoConnection,
) -> None:
    result = mongo_service.add_documents(
        "shop", "items", [{"name": "pen"}, {"name": "ink"}])

    assert (result.inserted, result.skipped) == (2, 0)
    assert {doc["name"] for doc in result.documents} == {"pen", "ink"}


def test_add_documents_skips_duplicates_but_keeps_the_rest(
    mongo_service: connection.MongoConnection,
) -> None:
    mongo_service.add_document("shop", "items", {"_id": 1})

    result = mongo_service.add_documents(
        "shop", "items", [{"_id": 1}, {"_id": 2}, {"_id": 3}])

    assert (result.inserted, result.skipped) == (2, 1)
    assert sorted(doc["_id"] for doc in result.documents) == [1, 2, 3]


def test_add_documents_keeps_identical_content_with_different_ids(
    mongo_service: connection.MongoConnection,
) -> None:
    mongo_service.add_document("shop", "items", {"name": "pen"})

    result = mongo_service.add_documents(
        "shop", "items", [
            {"_id": 10, "name": "pen"},
            {"_id": 11, "name": "ink"},
            {"_id": 12, "name": "ink"},
        ])

    assert (result.inserted, result.skipped) == (3, 0)
    assert len(result.documents) == 4


def test_add_documents_rejects_items_that_are_not_objects(
    mongo_service: connection.MongoConnection,
) -> None:
    with pytest.raises(ValueError, match="JSON object"):
        mongo_service.add_documents("shop", "items", [{"a": 1}, 5])  # type: ignore[list-item]


def test_add_documents_raises_when_every_document_is_rejected(
    mongo_service: connection.MongoConnection,
) -> None:
    mongo_service.add_document("shop", "items", {"_id": 1})

    with pytest.raises(ValueError, match="No documents were added"):
        mongo_service.add_documents("shop", "items", [{"_id": 1}])


def test_add_documents_rejects_empty_list(
    mongo_service: connection.MongoConnection,
) -> None:
    with pytest.raises(ValueError, match="no documents"):
        mongo_service.add_documents("shop", "items", [])


def test_add_documents_requires_connection() -> None:
    service = connection.MongoConnection("mongodb://cluster.example")

    with pytest.raises(ValueError, match="Connect to a MongoDB cluster"):
        service.add_documents("shop", "items", [{"a": 1}])
