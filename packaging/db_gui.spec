# PyInstaller build recipe for db-gui.exe.
#
# Author: Archer
#
# Build from the project root with the venv active:
#     pyinstaller packaging/db_gui.spec --noconfirm
# The finished app lands in the dist/arrow/ folder: arrow.exe plus an
# _internal/ folder holding Python and the libraries it needs. Send the WHOLE
# folder (zip it); arrow.exe won't start without _internal/ beside it.
# (The app is branded "Arrow_>", but Windows doesn't allow ">" in file names.)

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# SPECPATH is set by PyInstaller to this file's folder (packaging/).
ROOT = Path(SPECPATH).parent
SRC = ROOT / "src"

datas = [
    # Our icons. assets.py looks for them at db_gui/assets/ next to the code,
    # so they go to the same relative spot inside the bundle.
    (str(SRC / "db_gui" / "assets"), "db_gui/assets"),
]
# CustomTkinter loads its theme .json files from disk at runtime.
datas += collect_data_files("customtkinter")

# pymongo imports dnspython lazily (only for mongodb+srv:// Atlas URIs), so
# PyInstaller can't see it. Without this, Atlas logins fail in the .exe only.
hiddenimports = collect_submodules("dns")

a = Analysis(
    [str(ROOT / "packaging" / "launcher.py")],
    pathex=[str(SRC)],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["pytest", "mongomock"],  # test-only, keep the .exe smaller
)
pyz = PYZ(a.pure)

# One-folder build: the .exe holds only the launcher, and COLLECT copies the
# libraries/data next to it. Starts faster than a one-file build because
# nothing has to be unpacked to a temp folder on each launch.
exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="arrow",
    console=False,  # GUI app: don't open a black terminal window behind it
    upx=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="arrow",  # the output folder: dist/arrow/
    upx=False,
)
