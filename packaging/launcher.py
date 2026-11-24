"""Entry script PyInstaller freezes into db-gui.exe.

Author: Archer

main.py uses a relative import (`from .gui.app import App`), so PyInstaller
can't run it directly as a script. This file imports the package by its full
name instead and starts the app.
"""

from db_gui.main import main

if __name__ == "__main__":
    main()
