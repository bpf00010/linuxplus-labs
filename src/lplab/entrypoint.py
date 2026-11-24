import sys
from lplab.gui import main as gui_main, setup_safe_stdio


def main() -> None:
    is_console = False
    if sys.platform == "win32":
        import ctypes
        # Try attaching to parent console (e.g. PowerShell, cmd, Windows Terminal)
        if ctypes.windll.kernel32.AttachConsole(-1):
            is_console = True
            try:
                sys.stdout = open("CONOUT$", "w", encoding="utf-8", buffering=1)
                sys.stderr = open("CONOUT$", "w", encoding="utf-8", buffering=1)
            except Exception:
                pass
        elif ctypes.windll.kernel32.GetConsoleWindow() != 0:
            is_console = True

    if not is_console:
        # Launched with no parent console (e.g. double-clicked from File Explorer)
        setup_safe_stdio()
        if len(sys.argv) <= 1:
            gui_main()
            return

    if sys.stdout is None or sys.stderr is None:
        setup_safe_stdio()

    from lplab.cli import app
    app()


if __name__ == "__main__":
    main()
