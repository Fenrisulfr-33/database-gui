"""Remember-me storage: a local JSON list of clusters the user logged in to.

Author: Archer

See expected-behavior.md ("Login screen") for the rules this follows:
- An entry is only written after a SUCCESSFUL login with "Remember me" checked.
- Each entry has an optional `name` the user picks so it is easy to find later.
- Logging in again to the same cluster + username updates that entry instead
  of adding a duplicate.

The file lives in the user's home folder (not the repo) so saved logins can
never be committed by accident.

SECURITY NOTE (deferred): the password is stored in plain text for now. It
should later be encrypted or moved to the OS keyring.
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

SAVED_CLUSTERS_PATH = Path.home() / ".db_gui" / "saved_clusters.json"


@dataclass
class SavedCluster:
    """One remembered login. `name` is optional (empty string = no name)."""

    cluster: str
    username: str
    password: str
    name: str = ""

    def display_label(self) -> str:
        """Text shown in the saved-cluster picker, e.g. "Work (admin)".

        Author: Archer
        """
        # Fall back to the cluster address when the user gave no name.
        return f"{self.name or self.cluster} ({self.username})"


def load_saved_clusters(path: Path | None = None) -> list[SavedCluster]:
    """Return every saved cluster, or [] if the file is missing or unreadable.

    Author: Archer
    """
    path = path or SAVED_CLUSTERS_PATH
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        # Ignore anything that isn't a well-formed entry rather than crashing
        # the login screen over a hand-edited or corrupted file.
        return [_entry_from_dict(item) for item in data
                if _is_valid_entry(item)]
    except (OSError, ValueError, TypeError):
        return []


def save_cluster(entry: SavedCluster, path: Path | None = None) -> None:
    """Add the entry to the file, or update the one with the same login.

    Raises ValueError if the file can't be written.

    Author: Archer
    """
    path = path or SAVED_CLUSTERS_PATH
    entries = load_saved_clusters(path)
    existing = _find_entry(entries, entry)
    if existing is None:
        entries.append(entry)
    else:
        existing.password = entry.password
        # Keep the old name if the user left the name box empty this time.
        existing.name = entry.name or existing.name
    _write_entries(entries, path)


def _find_entry(entries: list[SavedCluster], entry: SavedCluster):
    """Return the saved entry with the same cluster + username, if any.

    Author: Archer
    """
    for saved in entries:
        if saved.cluster == entry.cluster and saved.username == entry.username:
            return saved
    return None


def _write_entries(entries: list[SavedCluster], path: Path) -> None:
    """Write the whole list back to the JSON file.

    Author: Archer
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps([asdict(entry) for entry in entries], indent=2)
        path.write_text(text, encoding="utf-8")
    except OSError as error:
        raise ValueError(
            f"Could not save the cluster: {error.strerror or error}") from error


def _is_valid_entry(item) -> bool:
    """True if a JSON item has the string fields a SavedCluster needs.

    Author: Archer
    """
    required = ("cluster", "username", "password")
    return isinstance(item, dict) and all(
        isinstance(item.get(key), str) for key in required)


def _entry_from_dict(item: dict) -> SavedCluster:
    """Build a SavedCluster from one JSON item (name defaults to "").

    Author: Archer
    """
    name = item.get("name")
    return SavedCluster(item["cluster"], item["username"], item["password"],
                        name if isinstance(name, str) else "")
