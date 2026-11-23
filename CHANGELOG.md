# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com),
and this project adheres to [Semantic Versioning](https://semver.org).

## 2026-11-23

### Added
- **Dashboard** (`gui/views/dashboard_view.py`), styled after `design/Dashboard.png`, replaces the old database home screen. It has a sidebar with a dropdown of collections for each database, a table of database stats (collections, documents, data size, storage size), a filter box, stat cards, a connection banner, a status bar, and **Create database** / **Refresh** buttons. The header is drawn but disabled except for the **Docs** link. Stats load on a background thread.
- Styled pop-ups (`gui/widgets/form_dialog.py`) for **Create database** (database name + first collection name) and **Rename database**, matching the pop-up designs in `design/`.
- In-app message pop-ups (`gui/widgets/message_dialog.py`), matching `design/Rename confirm popups.png`, replace every native `tkinter.messagebox` prompt (rename confirm, rename result/failure, "Cluster not saved"). Shared pop-up behavior (dimmed backdrop, centering, modal grab) lives in `gui/widgets/modal.py`.
- Styled `···` database feature menu (`gui/widgets/feature_menu.py`), matching `design/Database features.png`: pencil icon for Rename, green hover highlight, divider, and Close.
- **Remember me** on the login screen now saves successful logins to `~/.db_gui/saved_clusters.json` (`utils/saved_clusters.py`), with an optional cluster name and a dropdown to pick a saved cluster. Passwords are stored in plain text for now.
- `db/connection.py`: `list_database_stats()`, `get_database_stats()` and `get_cluster_status()`.
- Tests: `test_dashboard_view.py`, `test_connection_view.py`, `test_saved_clusters.py`, `test_form_dialog.py`, plus new tests in `test_connection.py` and `test_formatters.py`.

### Removed
- `gui/views/database_view.py` and `tests/test_database_view.py`. The dashboard replaces that screen.

## 2026-11-17

### Added
- Collections can now be opened. The new collection screen lists its documents and has **Add document** (type JSON in a pop-up) and **Import JSON file** (a JSON object, a list of objects, or JSON Lines) buttons. The list refreshes after each add.
- `db/connection.py` — `list_documents()`, `add_document()` and `add_documents()`. Documents whose `_id` already exists are skipped; everything else is added.
- `utils/` — JSON parsing (`validators.py`), document preview text (`formatters.py`) and file reading (`files.py`).
- Tests for the above in `tests/test_connection.py`, `test_validators.py`, `test_formatters.py`, `test_files.py` and `test_document_view.py`.

### Changed
- `gui/views/collection_view.py` — collection buttons are no longer disabled; clicking one opens its documents.
- `gui/app.py` — routes from the collection list to the new document screen.

## 2026-10-27

### Added
- Database rename by copy, verification, then source removal, with an approximate storage warning and recovery marker for interrupted copies.

## 2026-09-24

### Added
- `tests/test_connection.py` — `test_reconnect_closes_previous_client`, checking that calling `connect()` again closes the previous `MongoClient` before opening a new one.

## 2026-09-23

### Added
- `db/connection.py` — `MongoConnection` class that validates the cluster URI, username, and password, connects with a 5s server-selection timeout, pings the cluster, and returns a sorted list of visible databases. `close()` shuts down the client without keeping the credentials.
- `gui/views/connection_view.py` — `ConnectionView` login form (Cluster URI, Username, masked Password) with inline error messages. The password field is cleared after each submit.
- `gui/views/database_view.py` — `DatabaseView` "Database home" screen that lists the databases returned at login (buttons are disabled for now) and has a Disconnect button.
- `tests/test_connection.py` — tests for sorted database names, closing the client, and rejecting a missing URI or missing credentials (uses a fake client, no live MongoDB needed).

### Changed
- `gui/app.py` — the placeholder label is replaced by view routing: the app opens on `ConnectionView`, switches to `DatabaseView` after a successful login, and goes back to the login view on disconnect. Validation errors and `PyMongoError`s now show up in the form as a friendly error.

## 2026-09-21

### Added
- `src/db_gui/` package skeleton — `main.py` entry point and `gui/app.py` with an initial CustomTkinter `App` window (placeholder content, to be replaced by a connection view/sidebar once `db/connection.py` exists).
- `pyproject.toml` — project metadata, runtime dependencies (`customtkinter`, `pymongo`, `python-dotenv`), dev extras (`pytest`, `mongomock`), and the `db-gui` console script entry point.
- `SETUP.md` — dev environment setup instructions.
- `.env.example` — sample `MONGO_URI` for local MongoDB connection config.
- `.gitignore`.

## 2026-09-11

### Added
- `README.md` — project overview, branch/PR workflow, coding rules, testing expectations, and planned file structure.
- `CLAUDE.md` — guidance and project context for Claude Code sessions working in this repo.
- `CHANGELOG.md` — this file.

## - 2026-03-12 (Template)

### Added
- New `export_to_csv` function in the `analytics_processor` module.
- Automated retry logic for failed database network connections.

### Changed
- Increased data processor timeout limit from 30s to 60s to handle larger payload spikes.
- Optimized `chunk_size` memory allocation for production environments.

### Fixed
- Fixed a memory leak occurring when parsing corrupted JSON packets.
- Resolved type casting bug in data aggregation summaries.

### Removed
- Deprecated `legacy_parser` function (replaced by `v1.4.0` parser).