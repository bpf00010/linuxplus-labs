"""Unified entry point for lplab standalone executable and CLI."""

import sys
from lplab.gui import setup_safe_stdio
from lplab.cli import app


def main() -> None:
    setup_safe_stdio()
    app()


if __name__ == "__main__":
    main()
