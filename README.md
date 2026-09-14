# Database GUI

## Demo Branch

The demo branch serves as our `main` branch, this is where we will PR into to test features. 
If you want to work on some feature just make a branch called `demo-<first_name>`, then go through the normal PR process to merge into the `demo` branch.

## Rules

These rules are to help not rely so much on tickets or constant communication, these practices will help see into the mind of your peers and might just answer your question without having to ask them directly.

- Practice clean code.
- Function/variable names should be clear.
- Comment information you think is important for others to understand, more comments is better than less.
- At the top of each file you create put your name as an author.
- An functions you make/edit add a Author comment/update to what you did.
- Functions no bigger than 30 lines.
- Function arguments should be no more than 3.
- Refactor when you see necessary.
- Create functions with the idea of reusability.
- Create tests.
- Since this project will contain mostly python stick to `snake_case` variable naming.

## Testing

If you are working in a file lets say called `feature_x.py`, and you are working on function `add_collection_to_database`. Make a test file `test_*.py`, so `test_feature_x.py`, and the function name `test_add_collection_to_database`.

Ideally for this project we maintain over 75% code coverage if possible.

## Tickets/Issues

This is not cs314, a ticket should encapsulate an issue/feature like, allow users to add a collection to a specific database. This ticket would get picked up and would include everything in it, the functionality, the testing, the documentation, and connecting it to the whole program making sure it works the way intended. Then you would submit the PR, and if any issues occur, document it in the PR comments/review and go back until the feature/issue is complete.

## Commits

Commit as often as you want to your branch, the only thing I ask is you commit once a day on the day you code, so if you only code one function or 3 features at least commit once at the end of the day you worked on something.

## GUI framework

Tkinter - we choose this because its friendly to newcomers versus PySide which is industry standard and heavier learning curve.


## File Structure

This is a base template, we can change things as needed.

```
mongo-gui-manager/
├── README.md
├── requirements.txt
├── pyproject.toml
├── .env.example
├── .gitignore
│
├── src/
│   └── mongo_gui/
│       ├── __init__.py
│       ├── main.py                  # Entry point — launches the app
│       ├── config.py                # Settings, env var loading, constants
│       │
│       ├── db/                      # All MongoDB access logic (no GUI code here)
│       │   ├── __init__.py
│       │   ├── connection.py        # Connect/disconnect, client lifecycle
│       │   ├── database_ops.py      # create/list/drop databases
│       │   ├── collection_ops.py    # create/list/rename/drop collections
│       │   └── document_ops.py      # CRUD + queries on documents
│       │
│       ├── gui/                     # All UI code (calls into db/, never pymongo directly)
│       │   ├── __init__.py
│       │   ├── app.py               # Root window / App class, view routing
│       │   ├── theme.py             # Colors, fonts, CustomTkinter appearance
│       │   │
│       │   ├── views/               # Full-screen or full-panel views
│       │   │   ├── __init__.py
│       │   │   ├── connection_view.py   # Connect to a MongoDB URI
│       │   │   ├── database_view.py     # List/create/delete databases
│       │   │   ├── collection_view.py   # List/create/delete collections
│       │   │   └── document_view.py     # Table + editor for documents
│       │   │
│       │   └── widgets/             # Small reusable components
│       │       ├── __init__.py
│       │       ├── sidebar.py           # Database/collection tree nav
│       │       ├── data_table.py        # Paginated document table
│       │       ├── json_editor.py       # Raw JSON editor/validator widget
│       │       └── dialogs.py           # Confirm delete, create-new, error popups
│       │
│       └── utils/
│           ├── __init__.py
│           ├── validators.py        # Validate DB/collection names, JSON input
│           └── logger.py            # App-wide logging setup
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                  # Shared fixtures (test DB/client)
│   ├── test_database_ops.py
│   ├── test_collection_ops.py
│   ├── test_document_ops.py
│   └── test_validators.py
│
├── scripts/
│   └── seed_sample_data.py          # Populate a test DB with sample docs
│
└── docs/
    └── screenshots/                 # UI screenshots for the README
```