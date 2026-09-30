"""MongoDB connection lifecycle and cluster discovery."""

from pymongo import MongoClient
from pymongo.errors import PyMongoError


class MongoConnection:
    """Create, validate, and close a MongoDB cluster connection."""

    def __init__(self, uri: str) -> None:
        self._uri = uri.strip()
        self._client: MongoClient | None = None

    def connect(self, username: str, password: str) -> list[str]:
        """Connect to the cluster and return its visible databases."""
        if not self._uri or not username.strip() or not password:
            raise ValueError(
                "Cluster URI, username, and password are required.")

        self.close()
        self._client = MongoClient(
            self._uri,
            username=username.strip(),
            password=password,
            serverSelectionTimeoutMS=5000,
        )
        self._client.admin.command("ping")
        return sorted(self._client.list_database_names())

    def close(self) -> None:
        """Close the active client without retaining login credentials."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def create_database(
        self, database_name: str, collection_name: str
    ) -> list[str]:
        database_name = database_name.strip()
        collection_name = collection_name.strip()
        if not database_name or not collection_name:
            raise ValueError(
                "Database and initial collection names are required.")
        if self._client is None:
            raise ValueError(
                "Connect to a cluster before creating a database.")
        if database_name in self._client.list_database_names():
            raise ValueError("A database with that name already exists.")

        self._client[database_name].create_collection(collection_name)
        return sorted(self._client.list_database_names())


__all__ = ["MongoConnection", "PyMongoError"]
