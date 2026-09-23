"""Entry point for the Database GUI Manager.

Run from the project root (with your venv activated) as:

    python -m src.db_gui.main
"""

from .gui.app import App


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
