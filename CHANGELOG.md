# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com),
and this project adheres to [Semantic Versioning](https://semver.org).

## 2026-09-11

### Added
- `README.md` — project overview, branch/PR workflow, coding rules, testing expectations, and planned file structure.
- `CLAUDE.md` — guidance and project context for Claude Code sessions working in this repo.
- `CHANGELOG.md` — this file.

## - 2026-03-12 (Demo)

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