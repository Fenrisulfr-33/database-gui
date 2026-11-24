# Dev Setup

1. `cd` into root folder of project.
2. `pip install -e ".[dev]"`

	This installs the required packages, and the testing packages as dev so testing packages are not added in the build.

## Run

`db-gui`

## Build the .exe (Windows)

1. With the venv active and the dev extras installed (step 2 above), run from the project root:

    `pyinstaller packaging/db_gui.spec --noconfirm`

2. The app is written to the `dist/arrow/` folder: `arrow.exe` plus an `_internal/` folder it needs. To share it, zip the **whole** `arrow` folder (right-click → Send to → Compressed folder). The person unzips it and double-clicks `arrow.exe`. Any 64-bit Windows PC works, and that PC doesn't need Python installed. (The app is called "Arrow_>", but Windows doesn't allow `>` in file names, so the folder is `arrow`.)
3. `build/` and `dist/` are git-ignored. Don't commit the .exe. Share it some other way (e.g. a GitHub Release).

Notes:
- `arrow.exe` won't start if it's moved out of the folder, away from `_internal/`. Make a desktop shortcut to it instead.
- If you add new image files outside `src/db_gui/assets/`, or a new package that is imported lazily, add it to `packaging/db_gui.spec` or the .exe won't find it.
- Some antivirus tools flag new unsigned PyInstaller .exes. This is a false positive.

# Testing

1. To run all tests run `pytest`
2. to run a specific test run `pytest tests/<test_file_name>.py::test_reconnect_closes_previous_client 
    -v`
3. If `ModuleNotFoundErrorL No module named db_gui` error comes up the project isn't installed in the environment yet. Run `pip install -e ".[dev]"`, as seen above.