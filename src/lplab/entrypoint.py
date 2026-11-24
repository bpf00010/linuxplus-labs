"""Unified entry point for lplab standalone executable and CLI."""

import sys
from lplab.gui import hide_console_if_owned, setup_safe_stdio


def main() -> None:
    # 1. Double-clicked or run with no arguments -> launch Desktop GUI by default
    if len(sys.argv) <= 1:
        hide_console_if_owned()
        setup_safe_stdio()
        from lplab.gui import run_gui
        run_gui()
        return

    # 2. PowerShell / Terminal TUI opt-in: --tui, -t, tui, or ui
    first_arg = sys.argv[1].lower()
    if first_arg in ("--tui", "-t", "tui", "ui"):
        setup_safe_stdio()
        from lplab.config import load_config
        from lplab.tui import LabEngineApp
        config = load_config()
        app = LabEngineApp(config=config)
        app.run()
        return

    # 3. Explicit GUI command
    if first_arg == "gui":
        if "--browser" not in sys.argv:
            hide_console_if_owned()
        setup_safe_stdio()
        from lplab.cli import app as cli_app
        cli_app()
        return

    # 4. Standard CLI commands (list, start, verify, reset, stop, build-image, generate, --help)
    setup_safe_stdio()
    from lplab.cli import app as cli_app
    cli_app()


if __name__ == "__main__":
    main()
