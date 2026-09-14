# CLAUDE.md

Guidance for Claude Code when working in this repo. Keep this file up to date as the project evolves — stale instructions are worse than none.

## Project

Database GUI — a MongoDB manager built with Tkinter (chosen over PySide for its lower learning curve for newcomers). Team project; see `README.md` for branching model, ticket process, and full file structure.

## Conventions (from README — see README.md for the complete rules)

- Branch off `demo-<first_name>`, PR into `demo` (acts as `main`).
- `snake_case` for variables/functions (Python project).
- Functions ≤ 30 lines, ≤ 3 arguments.
- Author comment at the top of each file you create/edit, and an author note on functions you add/change.
- Comment generously — more context is preferred over less on this team.
- Write tests for new functionality: `tests/test_<file>.py`, functions named `test_<function_name>`. Target 75%+ coverage.
- `db/` code never touches the GUI layer directly, and `gui/` code never calls `pymongo` directly — it goes through `db/`.

## Environment & setup

- Python: latest 3.x (not pinned to a specific minor version yet — pin it in `pyproject.toml`/`requirements.txt` once dependencies are chosen).
- Package management: `venv` + `pip`.
- MongoDB for local dev: connection info lives in a `.env` file (not committed — see `.env.example` once it exists). Exact variable name(s) TBD.
- Running the app locally: TBD — expect a `run` entry point once `src/mongo_gui/main.py` exists.

## Running checks

- Tests: `pytest`.
- Linter/formatter: not chosen yet.
- Pre-commit hooks / CI gates: none set up yet.

## Team & process

- PR review: anyone on the team can review.
- PR size: one ticket per PR (see README's Tickets/Issues section for what a ticket should encapsulate).
- Ticket tracker: GitHub Projects.

## Current focus

Documentation, coding standards, and planning the overall architecture/layout (how the pieces connect) — implementation hasn't started yet.

## Open questions

Ask about these as they become relevant, or update this file directly when decided:
- Linter/formatter choice and its command.
- Pre-commit hooks / CI checks required before merge.
- Exact `.env` variable name(s) for the Mongo connection string.
- The actual local-run command once `main.py` exists.
- Anything explicitly out of scope or deferred for now.
- Any standing "always/never" preferences for how I should work in this repo.
