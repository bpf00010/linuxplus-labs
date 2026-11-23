import sys
from pathlib import Path


def is_frozen() -> bool:
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def get_bundle_dir() -> Path:
    if is_frozen():
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent.parent


def get_static_index_path() -> Path:
    if is_frozen():
        p1 = Path(sys._MEIPASS) / "lplab" / "static" / "index.html"
        if p1.is_file():
            return p1
        p2 = Path(sys._MEIPASS) / "static" / "index.html"
        if p2.is_file():
            return p2
    return Path(__file__).resolve().parent / "static" / "index.html"


def get_bundled_labs_dir() -> Path:
    if is_frozen():
        p = Path(sys._MEIPASS) / "labs"
        if p.is_dir():
            return p
    return get_bundle_dir() / "labs"
