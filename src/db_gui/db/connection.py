"""MongoDB connection lifecycle and cluster discovery."""

import hashlib
import os
import tempfile
from dataclasses import dataclass
from typing import BinaryIO

from bson import BSON
from bson.codec_options import CodecOptions
from pymongo import IndexModel, MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError


@dataclass
class _RenameOperation:
    client: MongoClient
    source_name: str
    target_name: str
    archive_path: str
    manifest: dict | None = None
    preserve_archive: bool = False


class MongoConnection:
    """Create, validate, and close a MongoDB cluster connection."""

    _ARCHIVE_MAGIC = b"DBGUI-BSON-1\n"
    _MAX_BSON_SIZE = 16 * 1024 * 1024

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

    def rename_database(self, source_name: str, target_name: str) -> str | None:
        """Stage a local BSON archive, then replace the source database.

        Returns the archive path only when cleanup fails. If automatic recovery
        fails, the archive is retained and its path is included in the error.
        """
        client, source = self._prepare_rename(source_name, target_name)
        metadata = list(source.list_collections())
        collections, views = self._split_metadata(metadata)
        archive_path = self._create_archive(source, collections, views)
        operation = _RenameOperation(
            client, source_name, target_name, archive_path
        )
        try:
            manifest = self._verify_archive(archive_path)
            operation.manifest = manifest
            self._verify_database(source, manifest)
            self._drop_source(operation)
            self._restore_target(operation)
        except Exception as error:
            if (
                not operation.preserve_archive
                and not self._remove_archive(archive_path)
            ):
                error.add_note(f"Local staging archive remains at '{archive_path}'.")
            raise
        return None if self._remove_archive(archive_path) else archive_path

    def _prepare_rename(
        self, source_name: str, target_name: str
    ) -> tuple[MongoClient, Database]:
        self._validate_rename(source_name, target_name)
        client = self._require_client()
        names = client.list_database_names()
        if source_name not in names:
            raise ValueError(f"Database '{source_name}' no longer exists.")
        if target_name in names:
            raise ValueError(f"Database '{target_name}' already exists.")
        return client, client.get_database(source_name)

    def _drop_source(self, operation: _RenameOperation) -> None:
        try:
            operation.client.drop_database(operation.source_name)
        except Exception as error:
            recovered, recovery_error = self._recover_source(operation, [])
            if not recovered:
                operation.preserve_archive = True
                raise RuntimeError(
                    "Could not confirm removal of the old database or "
                    "automatic recovery. Keep the local recovery archive at "
                    f"'{operation.archive_path}'. Recovery detail: "
                    f"{recovery_error}"
                ) from error
            raise RuntimeError(
                "The old database could not be removed. The original "
                "database is intact."
            ) from error

    def _restore_target(self, operation: _RenameOperation) -> None:
        target = operation.client.get_database(operation.target_name)
        created_content = []
        try:
            self._restore_archive(
                target, operation.archive_path, created_content
            )
            self._verify_database(target, operation.manifest)
        except Exception as error:
            recovered, recovery_error = self._recover_source(
                operation, created_content
            )
            if not recovered:
                operation.preserve_archive = True
                raise RuntimeError(
                    "The new database could not be verified and automatic "
                    "recovery failed. Keep the local recovery archive at "
                    f"'{operation.archive_path}'. Recovery detail: "
                    f"{recovery_error}"
                ) from error
            raise RuntimeError(
                "The new database could not be verified. The original "
                "database was restored from the local archive."
            ) from error

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

    @staticmethod
    def _split_metadata(metadata: list[dict]) -> tuple[list[dict], list[dict]]:
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

    def _create_archive(
        self, source, collections: list[dict], views: list[dict]
    ) -> str:
        """Write database contents and metadata to a local BSON stream."""
        handle = tempfile.NamedTemporaryFile(
            prefix="database-gui-", suffix=".bson", delete=False
        )
        archive_path = handle.name
        try:
            with handle:
                self._write_archive_contents(
                    handle, source, (collections, views)
                )
        except Exception as error:
            if not self._remove_archive(archive_path):
                error.add_note(f"Local staging archive remains at '{archive_path}'.")
            raise
        return archive_path

    def _write_archive_contents(
        self,
        archive: BinaryIO,
        source,
        sections: tuple[list[dict], list[dict]],
    ) -> None:
        collections, views = sections
        archive.write(self._ARCHIVE_MAGIC)
        for metadata in collections:
            self._write_collection_archive(archive, source, metadata)
        for view in views:
            self._write_record(archive, b"V", self._view_archive_metadata(view))
        self._write_record(
            archive,
            b"E",
            {
                "collections": [item["name"] for item in collections],
                "views": [item["name"] for item in views],
            },
        )

    def _write_collection_archive(
        self, archive: BinaryIO, source, metadata: dict
    ) -> None:
        name = metadata["name"]
        options = self._collection_options(metadata)
        source_collection = source[name]
        indexes = self._index_specs(source_collection)
        self._write_record(
            archive, b"C", {"name": name, "options": options, "indexes": indexes}
        )
        digest = hashlib.sha256()
        count = 0
        for document in source_collection.find({}).sort("_id", 1):
            encoded = self._write_document_record(
                archive, document, self._codec_options(source)
            )
            digest.update(encoded)
            count += 1
        self._write_record(
            archive, b"S", {"name": name, "count": count, "digest": digest.hexdigest()}
        )

    @staticmethod
    def _collection_options(metadata: dict) -> dict:
        options = dict(metadata.get("options", {}))
        options.pop("uuid", None)
        options.pop("idIndex", None)
        return options

    @staticmethod
    def _index_specs(collection) -> list[dict]:
        return [dict(index) for index in collection.list_indexes()]

    @staticmethod
    def _view_archive_metadata(metadata: dict) -> dict:
        return {"name": metadata["name"], "options": metadata.get("options", {})}

    @staticmethod
    def _codec_options(database_or_collection) -> CodecOptions:
        options = database_or_collection.codec_options
        if isinstance(options, CodecOptions):
            return options
        return CodecOptions()

    @staticmethod
    def _write_record(
        archive: BinaryIO,
        kind: bytes,
        value: dict,
    ) -> bytes:
        encoded = BSON.encode(value)
        archive.write(kind)
        archive.write(encoded)
        return encoded

    @staticmethod
    def _write_document_record(
        archive: BinaryIO, document: dict, codec_options: CodecOptions
    ) -> bytes:
        encoded = BSON.encode(document, codec_options=codec_options)
        archive.write(b"D")
        archive.write(encoded)
        return encoded

    def _verify_archive(self, archive_path: str) -> dict:
        """Read the whole archive and verify its structure and document digests."""
        manifest = {"collections": {}, "views": []}
        with open(archive_path, "rb") as archive:
            if archive.read(len(self._ARCHIVE_MAGIC)) != self._ARCHIVE_MAGIC:
                raise RuntimeError("The local BSON archive has an invalid header.")
            self._read_archive_records(archive, manifest)
        return manifest

    def _read_archive_records(self, archive: BinaryIO, manifest: dict) -> None:
        state = {"active": None, "digest": None, "count": 0}
        while True:
            record = self._read_record(archive)
            if record is None:
                raise RuntimeError("The local BSON archive is incomplete.")
            if self._process_archive_record(record, manifest, state):
                if archive.read(1):
                    raise RuntimeError("The local BSON archive has trailing data.")
                return

    def _process_archive_record(
        self, record: tuple[bytes, dict, bytes], manifest: dict, state: dict
    ) -> bool:
        kind, value, encoded = record
        if kind == b"C":
            state["active"], state["digest"], state["count"] = (
                self._begin_archive_collection(value, manifest, state["active"])
            )
        elif kind == b"D":
            if state["active"] is None:
                raise RuntimeError("The local BSON archive has misplaced data.")
            state["digest"].update(encoded)
            state["count"] += 1
        elif kind == b"S":
            self._finish_archive_collection(
                value, state["active"], (state["digest"], state["count"])
            )
            state.update(active=None, digest=None, count=0)
        elif kind == b"V":
            if state["active"] is not None:
                raise RuntimeError("The local BSON archive has misplaced views.")
            manifest["views"].append(value)
        elif kind == b"E":
            self._verify_archive_footer(value, manifest, state["active"])
            return True
        else:
            raise RuntimeError("The local BSON archive contains an unknown record.")
        return False

    @staticmethod
    def _begin_archive_collection(
        value: dict, manifest: dict, active
    ) -> tuple[dict, object, int]:
        name = value.get("name")
        if active is not None or not name or name in manifest["collections"]:
            raise RuntimeError("The local BSON archive has invalid collection metadata.")
        collection = {"name": name, "options": value["options"],
                      "indexes": value["indexes"]}
        manifest["collections"][name] = collection
        return collection, hashlib.sha256(), 0

    @staticmethod
    def _finish_archive_collection(value: dict, active, totals: tuple) -> None:
        digest, count = totals
        if active is None or value.get("name") != active["name"]:
            raise RuntimeError("The local BSON archive has invalid collection data.")
        if value.get("count") != count or value.get("digest") != digest.hexdigest():
            raise RuntimeError(f"The local archive data for '{active['name']}' is corrupt.")
        active["count"] = count
        active["digest"] = digest.hexdigest()

    @classmethod
    def _read_record(
        cls, archive: BinaryIO, codec_options: CodecOptions | None = None
    ) -> tuple[bytes, dict, bytes] | None:
        kind = archive.read(1)
        if not kind:
            return None
        length_header = archive.read(4)
        if len(length_header) != 4:
            raise RuntimeError("The local BSON archive contains a truncated record.")
        length = int.from_bytes(length_header, "little", signed=True)
        if length < 5 or length > cls._MAX_BSON_SIZE:
            raise RuntimeError("The local BSON archive contains an invalid record size.")
        encoded = length_header + archive.read(length - 4)
        if len(encoded) != length:
            raise RuntimeError("The local BSON archive contains a truncated record.")
        if kind == b"D" and codec_options is not None:
            value = BSON(encoded).decode(codec_options=codec_options)
        else:
            value = BSON(encoded).decode()
        return kind, value, encoded

    @staticmethod
    def _verify_archive_footer(value: dict, manifest: dict, active) -> None:
        if active is not None:
            raise RuntimeError("The local BSON archive ends inside a collection.")
        if value.get("collections") != list(manifest["collections"]):
            raise RuntimeError("The local BSON archive collection list is invalid.")
        if value.get("views") != [view["name"] for view in manifest["views"]]:
            raise RuntimeError("The local BSON archive view list is invalid.")

    @staticmethod
    def _restore_archive(
        target, archive_path: str, created_content: list[str] | None = None
    ) -> None:
        if created_content is None:
            created_content = []
        with open(archive_path, "rb") as archive:
            archive.seek(len(MongoConnection._ARCHIVE_MAGIC))
            views = MongoConnection._restore_collection_records(
                target, archive, created_content
            )
        MongoConnection._restore_views(target, views, created_content)

    @staticmethod
    def _restore_collection_records(
        target, archive: BinaryIO, created_content: list[str]
    ) -> list[dict]:
        state = {
            "target": target,
            "created_content": created_content,
            "views": [],
            "collection": None,
            "indexes": [],
            "batch": [],
        }
        while True:
            record = MongoConnection._read_record(
                archive, MongoConnection._codec_options(target)
            )
            if record is None:
                raise RuntimeError("The local BSON archive is incomplete.")
            if MongoConnection._restore_record(record, state):
                return state["views"]

    @staticmethod
    def _restore_record(record: tuple[bytes, dict, bytes], state: dict) -> bool:
        kind, value, _ = record
        target = state["target"]
        if kind == b"C":
            state["collection"] = target.create_collection(
                value["name"], **value["options"]
            )
            state["created_content"].append(value["name"])
            state["indexes"] = value["indexes"]
        elif kind == b"D":
            state["batch"].append(value)
            if len(state["batch"]) == 500:
                MongoConnection._insert_batch(state["collection"], state["batch"])
                state["batch"].clear()
        elif kind == b"S":
            if state["batch"]:
                MongoConnection._insert_batch(state["collection"], state["batch"])
                state["batch"].clear()
            MongoConnection._create_indexes(state["collection"], state["indexes"])
        elif kind == b"V":
            state["views"].append(value)
        elif kind == b"E":
            return True
        else:
            raise RuntimeError("The local BSON archive contains an unknown record.")
        return False

    @staticmethod
    def _restore_views(
        target, views: list[dict], created_content: list[str]
    ) -> None:
        for view in views:
            options = dict(view["options"])
            view_on = options.pop("viewOn")
            pipeline = options.pop("pipeline")
            target.create_collection(
                view["name"], viewOn=view_on, pipeline=pipeline, **options
            )
            created_content.append(view["name"])

    @staticmethod
    def _insert_batch(collection, batch: list[dict]) -> None:
        collection.insert_many(batch, bypass_document_validation=True)

    @staticmethod
    def _create_indexes(collection, indexes: list[dict]) -> None:
        models = []
        for index in indexes:
            if index["name"] == "_id_":
                continue
            options = {key: value for key, value in index.items()
                       if key not in {"key", "ns", "v"}}
            models.append(IndexModel(index["key"], **options))
        if models:
            collection.create_indexes(models)

    def _verify_database(self, database, manifest: dict) -> None:
        collections = manifest["collections"]
        views = manifest["views"]
        expected = set(collections) | {view["name"] for view in views}
        metadata = list(database.list_collections())
        actual = {item["name"] for item in metadata}
        if actual != expected:
            raise RuntimeError("The restored database's collections do not match.")
        self._verify_database_collections(database, metadata, collections)
        self._verify_database_views(metadata, views)

    def _verify_database_collections(
        self, database, metadata: list[dict], collections: dict
    ) -> None:
        actual_metadata = {item["name"]: item for item in metadata}
        for name, expected in collections.items():
            collection = database[name]
            actual_options = self._collection_options(actual_metadata[name])
            if actual_options != expected["options"]:
                raise RuntimeError(f"'{name}' has different collection options.")
            count, digest = self._collection_digest(collection)
            if count != expected["count"] or digest != expected["digest"]:
                raise RuntimeError(f"'{name}' has different data after restoring.")
            if self._index_signatures(collection) != self._index_signatures(
                expected["indexes"]
            ):
                raise RuntimeError(f"'{name}' has different indexes after restoring.")

    @staticmethod
    def _collection_digest(collection) -> tuple[int, str]:
        digest = hashlib.sha256()
        count = 0
        for document in collection.find({}).sort("_id", 1):
            digest.update(
                BSON.encode(
                    document,
                    codec_options=MongoConnection._codec_options(collection),
                )
            )
            count += 1
        return count, digest.hexdigest()

    @staticmethod
    def _verify_database_views(metadata: list[dict], views: list[dict]) -> None:
        actual_views = [item for item in metadata if item["type"] == "view"]
        expected = {item["name"]: MongoConnection._view_signature(item) for item in views}
        actual = {item["name"]: MongoConnection._view_signature(item)
                  for item in actual_views}
        if actual != expected:
            raise RuntimeError("The restored database's views do not match.")

    @staticmethod
    def _index_signatures(collection) -> list[dict]:
        indexes = collection if isinstance(collection, list) else collection.list_indexes()
        return [
            {key: value for key, value in index.items() if key != "ns"}
            for index in indexes
        ]

    @staticmethod
    def _view_signature(metadata: dict) -> tuple:
        options = metadata.get("options", {})
        return (
            options.get("viewOn"),
            options.get("pipeline"),
            options.get("collation"),
        )

    def _recover_source(
        self,
        operation: _RenameOperation,
        created_content: list[str],
    ) -> tuple[bool, str | None]:
        target_error = self._remove_created_content(
            operation.client.get_database(operation.target_name), created_content
        )
        try:
            source = operation.client.get_database(operation.source_name)
            if operation.source_name not in operation.client.list_database_names():
                self._restore_archive(source, operation.archive_path)
            self._verify_database(source, operation.manifest)
        except Exception as error:
            detail = str(error)
            if target_error:
                detail = f"{target_error}; {detail}"
            return False, detail
        if target_error:
            return False, f"Could not remove the partial new database: {target_error}"
        return True, None

    @staticmethod
    def _remove_created_content(database, names: list[str]) -> str | None:
        for name in names:
            try:
                database.drop_collection(name)
            except Exception as error:
                return f"Could not remove partial collection '{name}': {error}"
        return None

    @staticmethod
    def _remove_archive(archive_path: str) -> bool:
        try:
            os.remove(archive_path)
        except OSError:
            return False
        return True


__all__ = ["MongoConnection", "PyMongoError"]