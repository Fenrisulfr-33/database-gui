"""Read files the user picks."""

from pathlib import Path

# the whole file is loaded at once, so don't allow huge ones
MAX_IMPORT_BYTES = 20 * 1024 * 1024


def read_text_file(path: str) -> str:
    """Return the text of a UTF-8 file."""
    try:
        file_path = Path(path)
        if file_path.stat().st_size > MAX_IMPORT_BYTES:
            limit_mb = MAX_IMPORT_BYTES // (1024 * 1024)
            raise ValueError(f"The file is larger than {limit_mb} MB.")
        # utf-8-sig so a BOM from Windows editors doesn't break the JSON
        return file_path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError("The file is not UTF-8 text.") from error
    except OSError as error:
        raise ValueError(
            f"Could not read the file: {error.strerror or error}") from error
