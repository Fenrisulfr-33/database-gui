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


# --- dashboard stats (Author: Archer) ---

class _StatsDatabase:
    """Stands in for a pymongo Database that answers dbStats."""

    def __init__(self, stats):
        self._stats = stats

    def command(self, name):
        if isinstance(self._stats, Exception):
            raise self._stats
        return self._stats


class _StatsClient:
    def __init__(self, stats_by_name):
        self._stats_by_name = stats_by_name

    def list_database_names(self):
        return list(self._stats_by_name)

    def get_database(self, name):
        return _StatsDatabase(self._stats_by_name[name])


def _stats_service(stats_by_name) -> connection.MongoConnection:
    service = connection.MongoConnection("mongodb+srv://u:p@c0.example.net/?x=1")
    service._client = _StatsClient(stats_by_name)
    return service


def test_get_database_stats_reads_db_stats_and_adds_indexes() -> None:
    service = _stats_service({"shop": {
        "collections": 3, "objects": 10.0, "dataSize": 500.0,
        "storageSize": 800.0, "indexSize": 200.0}})

    stats = service.get_database_stats("shop")

    assert stats == connection.DatabaseStats("shop", 3, 10, 500, 1000,
                                             index_size=200)


def test_get_database_stats_returns_blanks_when_command_fails() -> None:
    from pymongo.errors import OperationFailure
    service = _stats_service({"local": OperationFailure("not authorized")})

    assert service.get_database_stats("local") == connection.DatabaseStats("local")


def test_list_database_stats_is_sorted_by_name() -> None:
    service = _stats_service({"b": {}, "a": {}})

    assert [db.name for db in service.list_database_stats()] == ["a", "b"]


def test_host_from_uri_strips_credentials_and_options() -> None:
    assert connection._host_from_uri(
        "mongodb+srv://u:p@c0.example.net/?x=1") == "c0.example.net"
    assert connection._host_from_uri("mongodb://localhost:27017") == \
        "localhost:27017"


def test_get_cluster_status_reports_ping_version_and_replica_set() -> None:
    class Admin:
        def command(self, name):
            return {"setName": "rs0"} if name == "hello" else {"ok": 1}

    class Client:
        admin = Admin()

        def server_info(self):
            return {"version": "7.0.14"}

    service = connection.MongoConnection("mongodb://c0.example.net")
    service._client = Client()

    status = service.get_cluster_status()

    assert status.host == "c0.example.net"
    assert status.ping_ms is not None
    assert (status.version, status.replica_set) == ("7.0.14", "rs0")


# --- Collections page (Author: Archer) ---

def test_count_fields_unions_top_level_keys() -> None:
    # mongomock can't run $collStats, so test the field count on its own.
    _service, client = _connected_service()
    client["shop"]["orders"].insert_many([{"a": 1, "b": 2}, {"a": 3, "c": 4}])

    assert connection._count_fields(client["shop"]["orders"]) == 4  # _id,a,b,c


def test_get_collection_stats_keeps_blanks_when_coll_stats_fails() -> None:
    from pymongo.errors import OperationFailure

    class Collection:
        def find(self, _filter, limit):
            return [{"_id": 1, "x": 1}]

        def aggregate(self, _pipeline):
            raise OperationFailure("views have no storage stats")

    service = connection.MongoConnection("mongodb://c0")
    service._client = {"shop": {"v": Collection()}}

    stats = service.get_collection_stats("shop", "v")

    assert stats == connection.CollectionStats("v", fields=2)


def test_get_collection_stats_reads_storage_stats() -> None:
    class Collection:
        def find(self, _filter, limit):
            return []

        def aggregate(self, _pipeline):
            return iter([{"storageStats": {
                "count": 5, "size": 500.0, "nindexes": 2,
                "totalIndexSize": 64.0}}])

    service = connection.MongoConnection("mongodb://c0")
    service._client = {"shop": {"orders": Collection()}}

    assert service.get_collection_stats("shop", "orders") == \
        connection.CollectionStats("orders", 5, 500, 2, 64, 0)


def test_rename_collection_renames_in_place() -> None:
    service, client = _connected_service()
    client["shop"]["orders"].insert_one({"a": 1})

    service.rename_collection("shop", "orders", " sales ")

    assert client["shop"].list_collection_names() == ["sales"]


@pytest.mark.parametrize("name", ["", "bad$name", "system.users"])
def test_rename_collection_rejects_invalid_names(name: str) -> None:
    service, _client = _connected_service()

    with pytest.raises(ValueError):
        service.rename_collection("shop", "orders", name)


def test_rename_collection_reports_taken_name() -> None:
    from pymongo.errors import OperationFailure

    class Collection:
        def rename(self, _new):
            raise OperationFailure("exists", code=connection.NAMESPACE_EXISTS)

    service = connection.MongoConnection("mongodb://c0")
    service._client = {"shop": {"orders": Collection()}}

    with pytest.raises(ValueError, match="already exists"):
        service.rename_collection("shop", "orders", "sales")


# --- Collection schemas (Author: Archer) ---
# mongomock can't run collMod or $jsonSchema, so these use small fakes that
# record what MongoConnection sends to MongoDB.

STRICT_SCHEMA = {"bsonType": "object", "additionalProperties": False,
                 "properties": {"_id": {}, "name": {"bsonType": "string"}},
                 "required": ["name"]}


class SchemaCollection:
    """Record the queries sent to one collection."""

    def __init__(self, found: list[dict]) -> None:
        self.found = found
        self.queries: list[dict] = []

    def count_documents(self, query: dict) -> int:
        self.queries.append(query)
        return len(self.found)

    def find(self, query: dict, projection: dict) -> list[dict]:
        self.queries.append(query)
        return self.found


class SchemaDatabase:
    """Fake database whose collection options hold `validator`."""

    def __init__(self, validator=None, found=None, exists=True) -> None:
        options = {} if validator is None else {"validator": validator}
        self.infos = [{"name": "people", "options": options}] if exists else []
        self.commands: list[tuple] = []
        self.collection = SchemaCollection(found or [])

    def list_collections(self, filter: dict) -> list[dict]:
        assert filter == {"name": "people"}
        return self.infos

    def command(self, *args, **kwargs) -> dict:
        self.commands.append((args, kwargs))
        return {"ok": 1}

    def __getitem__(self, _name: str) -> SchemaCollection:
        return self.collection


def _schema_service(database: SchemaDatabase) -> connection.MongoConnection:
    service = connection.MongoConnection("mongodb://c0")
    service._client = {"shop": database}
    return service


def test_get_collection_schema_returns_inner_json_schema() -> None:
    service = _schema_service(SchemaDatabase({"$jsonSchema": STRICT_SCHEMA}))

    assert service.get_collection_schema("shop", "people") == STRICT_SCHEMA


def test_get_collection_schema_returns_none_without_validator() -> None:
    service = _schema_service(SchemaDatabase())

    assert service.get_collection_schema("shop", "people") is None


def test_get_collection_schema_rejects_query_validators() -> None:
    validator = {"$jsonSchema": STRICT_SCHEMA, "age": {"$gt": 0}}
    service = _schema_service(SchemaDatabase(validator))

    with pytest.raises(connection.UnsupportedSchemaError):
        service.get_collection_schema("shop", "people")


def test_get_collection_schema_reports_missing_collection() -> None:
    service = _schema_service(SchemaDatabase(exists=False))

    with pytest.raises(ValueError, match="doesn't exist"):
        service.get_collection_schema("shop", "people")


def test_set_collection_schema_saves_strict_validator() -> None:
    database = SchemaDatabase()

    _schema_service(database).set_collection_schema(
        "shop", "people", STRICT_SCHEMA)

    assert database.commands == [(
        ("collMod", "people"),
        {"validator": {"$jsonSchema": STRICT_SCHEMA},
         "validationLevel": "strict", "validationAction": "error"},
    )]


def test_set_collection_schema_rejects_unsupported_before_saving() -> None:
    database = SchemaDatabase()
    schema = dict(STRICT_SCHEMA, title="extra")

    with pytest.raises(connection.UnsupportedSchemaError):
        _schema_service(database).set_collection_schema("shop", "people", schema)
    assert database.commands == []


def test_set_collection_schema_reports_server_rejection() -> None:
    from pymongo.errors import OperationFailure

    database = SchemaDatabase()

    def refuse(*_args, **_kwargs):
        raise OperationFailure("bad", details={"errmsg": "not allowed"})

    database.command = refuse

    with pytest.raises(ValueError, match="not allowed"):
        _schema_service(database).set_collection_schema(
            "shop", "people", STRICT_SCHEMA)


def test_remove_collection_schema_clears_validator() -> None:
    database = SchemaDatabase({"$jsonSchema": STRICT_SCHEMA})

    _schema_service(database).remove_collection_schema("shop", "people")

    assert database.commands == [(
        ("collMod", "people"), {"validator": {}, "validationLevel": "off"})]


def test_count_schema_mismatches_counts_documents_failing_schema() -> None:
    database = SchemaDatabase(found=[{"_id": 1}, {"_id": 2}])

    count = _schema_service(database).count_schema_mismatches(
        "shop", "people", STRICT_SCHEMA)

    assert count == 2
    assert database.collection.queries == [
        {"$nor": [{"$jsonSchema": STRICT_SCHEMA}]}]


def test_find_schema_mismatches_checks_only_given_ids() -> None:
    database = SchemaDatabase({"$jsonSchema": STRICT_SCHEMA},
                              found=[{"_id": 2}])

    broken = _schema_service(database).find_schema_mismatches(
        "shop", "people", [1, 2])

    assert broken == {2}
    assert database.collection.queries == [
        {"_id": {"$in": [1, 2]}, "$nor": [{"$jsonSchema": STRICT_SCHEMA}]}]


def test_find_schema_mismatches_is_empty_without_schema() -> None:
    database = SchemaDatabase(found=[{"_id": 2}])

    assert _schema_service(database).find_schema_mismatches(
        "shop", "people", [1, 2]) == set()
    assert database.collection.queries == []


def test_add_document_reports_schema_rejection() -> None:
    from pymongo.errors import WriteError

    class Collection:
        def insert_one(self, _document):
            raise WriteError("failed",
                             code=connection.DOCUMENT_VALIDATION_FAILURE)

    service = connection.MongoConnection("mongodb://c0")
    service._client = {"shop": {"people": Collection()}}

    with pytest.raises(ValueError, match="doesn't match"):
        service.add_document("shop", "people", {"name": 5})
