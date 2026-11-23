import sys
from lplab.gui import main as gui_main, setup_safe_stdio


def main() -> None:
    setup_safe_stdio()
    if len(sys.argv) <= 1:
        gui_main()
    else:
        if sys.platform == "win32":
            import ctypes
            if ctypes.windll.kernel32.AttachConsole(-1):
                try:
                    sys.stdout = open("CONOUT$", "w", encoding="utf-8", buffering=1)
                    sys.stderr = open("CONOUT$", "w", encoding="utf-8", buffering=1)
                except Exception:
                    pass

        from lplab.cli import app
        app()


if __name__ == "__main__":
    main()
