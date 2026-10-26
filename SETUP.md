# Dev Setup

1. `cd` into root folder of project.
2. `pip install -e ".[dev]"`

	This installs the required packages, and the testing packages as dev so testing packages are not added in the build.

## Run

`db-gui`

# Testing

1. To run all tests run `pytest`
2. to run a specific test run `pytest tests/<test_file_name>.py::test_reconnect_closes_previous_client 
    -v`
3. If `ModuleNotFoundErrorL No module named db_gui` error comes up the project isn't installed in the environment yet. Run `pip install -e ".[dev]"`, as seen above.