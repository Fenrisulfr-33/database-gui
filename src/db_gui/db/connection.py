"""MongoDB connection lifecycle and cluster discovery."""

from datetime import datetime, timezone

from pymongo import IndexModel, MongoClient
from pymongo.errors import PyMongoError


class MongoConnection:
    """Create, validate, and close a MongoDB cluster connection."""

    _RENAME_STATE_COLLECTION = "_database_gui_rename_state"

    def __init__(self, uri: str) -> None:
        self._uri = uri.strip()
        self._client: MongoClient | None = None

    def connect(self, username: str, password: str) -> list[str]:
        """Connect to the cluster and return its visible databases."""
        if not self._uri or not username.strip() or not password:
            raise ValueError("Cluster URI, username, and password are required.")

        self.close()
        self._client = MongoClient(
            self._uri,
            username=username.strip(),
            password=password,
            serverSelectionTimeoutMS=5000,
        )
        self._client.admin.command("ping")
        return self.list_databases()

    def close(self) -> None:
        """Close the active client without retaining login credentials."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def list_databases(self) -> list[str]:
        """Return the names of databases visible to the active user."""
        return sorted(self._require_client().list_database_names())

    def get_database_size(self, database_name: str) -> int | None:
        """Return an approximate database data-and-index size in bytes."""
        try:
            stats = self._require_client().get_database(database_name).command(
                "dbStats"
            )
        except PyMongoError:
            return None
        data_size = stats.get("dataSize")
        index_size = stats.get("indexSize")
        if data_size is None or index_size is None:
            return None
        return int(data_size + index_size)

    def rename_database(self, source_name: str, target_name: str) -> bool:
        """Copy and verify a database before dropping its source.

        Returns True when the temporary recovery marker was removed. A failed
        copy leaves the source intact and marks the partial destination.
        """
        self._validate_rename(source_name, target_name)
        client = self._require_client()
        names = client.list_database_names()
        if source_name not in names:
            raise ValueError(f"Database '{source_name}' no longer exists.")
        if target_name in names:
            raise ValueError(f"Database '{target_name}' already exists.")

        source = client.get_database(source_name)
        target = client.get_database(target_name)
        metadata = list(source.list_collections())
        collections, views = self._split_metadata(metadata)
        self._start_copy(target, source_name, target_name)
        for item in collections:
            self._copy_collection(source, target, item)
        for item in views:
            self._copy_view(target, item)
        self._verify_copy(source, target, collections, views)
        target[self._RENAME_STATE_COLLECTION].update_one(
            {"_id": "rename"}, {"$set": {"status": "verified"}}
        )
        client.drop_database(source_name)
        return self._remove_rename_marker(client, target_name)

    def _require_client(self) -> MongoClient:
        if self._client is None:
            raise ValueError("Connect to a MongoDB cluster first.")
        return self._client

    @staticmethod
    def _validate_rename(source_name: str, target_name: str) -> None:
        invalid = set('/\\."$')
        if (
            not target_name
            or "\0" in target_name
            or invalid.intersection(target_name)
        ):
            raise ValueError("Enter a valid MongoDB database name.")
        if len(target_name.encode("utf-8")) > 64:
            raise ValueError("Database names must be at most 64 bytes.")
        if source_name == target_name:
            raise ValueError("The new database name must be different.")
        if source_name in {"admin", "local", "config"} or target_name in {
            "admin",
            "local",
            "config",
        }:
            raise ValueError("System databases cannot be renamed.")

    def _split_metadata(self, metadata: list[dict]) -> tuple[list[dict], list[dict]]:
        if any(item["name"] == self._RENAME_STATE_COLLECTION for item in metadata):
            raise ValueError(
                f"The source uses the reserved collection "
                f"'{self._RENAME_STATE_COLLECTION}'."
            )
        collections = [item for item in metadata if item["type"] == "collection"]
        views = [item for item in metadata if item["type"] == "view"]
        unsupported = [
            item["name"]
            for item in metadata
            if item["type"] not in {"collection", "view"}
        ]
        if unsupported:
            raise ValueError(
                "Cannot safely rename databases containing unsupported "
                f"collection types: {', '.join(unsupported)}."
            )
        return collections, views

    def _start_copy(self, target, source_name: str, target_name: str) -> None:
        target.create_collection(self._RENAME_STATE_COLLECTION)
        target[self._RENAME_STATE_COLLECTION].insert_one(
            {
                "_id": "rename",
                "source": source_name,
                "target": target_name,
                "status": "copying",
                "started_at": datetime.now(timezone.utc),
            }
        )

    @staticmethod
    def _copy_collection(source, target, metadata: dict) -> None:
        name = metadata["name"]
        options = dict(metadata.get("options", {}))
        options.pop("uuid", None)
        options.pop("idIndex", None)
        target.create_collection(name, **options)
        source_collection = source[name]
        target_collection = target[name]
        batch = []
        copied = 0
        for document in source_collection.find({}):
            batch.append(document)
            if len(batch) == 500:
                target_collection.insert_many(batch, bypass_document_validation=True)
                copied += len(batch)
                batch.clear()
        if batch:
            target_collection.insert_many(batch, bypass_document_validation=True)
            copied += len(batch)
        if source_collection.count_documents({}) != copied:
            raise RuntimeError(f"'{name}' changed or was not fully copied.")
        MongoConnection._copy_indexes(source_collection, target_collection)

    @staticmethod
    def _copy_indexes(source_collection, target_collection) -> None:
        indexes = []
        for index in source_collection.list_indexes():
            if index["name"] == "_id_":
                continue
            options = {
                key: value
                for key, value in index.items()
                if key not in {"key", "ns", "v"}
            }
            indexes.append(IndexModel(index["key"], **options))
        if indexes:
            target_collection.create_indexes(indexes)

    @staticmethod
    def _copy_view(target, metadata: dict) -> None:
        options = metadata.get("options", {})
        view_options = {"viewOn": options["viewOn"], "pipeline": options["pipeline"]}
        if "collation" in options:
            view_options["collation"] = options["collation"]
        target.create_collection(metadata["name"], **view_options)

    def _verify_copy(
        self, source, target, collections: list[dict], views: list[dict]
    ) -> None:
        expected = {item["name"] for item in collections + views}
        actual = set(target.list_collection_names())
        actual.discard(self._RENAME_STATE_COLLECTION)
        if actual != expected:
            raise RuntimeError("The copied database's collections do not match.")
        for item in collections:
            name = item["name"]
            if source[name].count_documents({}) != target[name].count_documents({}):
                raise RuntimeError(f"'{name}' has a different document count.")
            if self._index_signatures(source[name]) != self._index_signatures(
                target[name]
            ):
                raise RuntimeError(f"'{name}' has different indexes after copying.")
        source_views = {item["name"] for item in views}
        target_view_metadata = [
            item for item in target.list_collections() if item["type"] == "view"
        ]
        if source_views != {item["name"] for item in target_view_metadata}:
            raise RuntimeError("The copied database's views do not match.")
        source_signatures = {
            item["name"]: self._view_signature(item) for item in views
        }
        target_signatures = {
            item["name"]: self._view_signature(item) for item in target_view_metadata
        }
        if source_signatures != target_signatures:
            raise RuntimeError("The copied database's view definitions do not match.")

    @staticmethod
    def _index_signatures(collection) -> list[dict]:
        return [
            {key: value for key, value in index.items() if key != "ns"}
            for index in collection.list_indexes()
        ]

    @staticmethod
    def _view_signature(metadata: dict) -> tuple:
        options = metadata.get("options", {})
        return (
            options.get("viewOn"),
            options.get("pipeline"),
            options.get("collation"),
        )

    def _remove_rename_marker(self, client, target_name: str) -> bool:
        try:
            client.get_database(target_name).drop_collection(
                self._RENAME_STATE_COLLECTION
            )
        except PyMongoError:
            return False
        return True


__all__ = ["MongoConnection", "PyMongoError"]