# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com),
and this project adheres to [Semantic Versioning](https://semver.org).

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