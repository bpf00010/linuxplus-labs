"""Native desktop GUI window launcher for lplab using pywebview and uvicorn."""

import os
import socket
import sys
import threading
import time
import urllib.request
from pathlib import Path
from typing import Optional
import uvicorn


def get_gui_log_path() -> Path:
    """Return the absolute path to gui.log, ensuring parent directories exist."""
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            base_dir = Path(local_app_data) / "linuxplus-labs"
        else:
            base_dir = Path.home() / "AppData" / "Local" / "linuxplus-labs"
    else:
        state_home = os.environ.get("XDG_STATE_HOME")
        if state_home:
            base_dir = Path(state_home) / "lplab"
        else:
            base_dir = Path.home() / ".local" / "state" / "lplab"
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / "gui.log"


def setup_safe_stdio(force_redirect: bool = False) -> Path:
    """Ensure sys.stdout and sys.stderr are valid file-like streams.

    Under pythonw.exe or hidden console on Windows, redirects sys.stdout and sys.stderr
    to gui.log in append mode to avoid crashes and capture all server logs.
    """
    log_path = get_gui_log_path()
    if force_redirect or sys.stdout is None or sys.stderr is None:
        log_file = open(log_path, "a", encoding="utf-8", buffering=1)
        if force_redirect or sys.stdout is None:
            sys.stdout = log_file
        if force_redirect or sys.stderr is None:
            sys.stderr = log_file
    return log_path


def find_free_port(host: str = "127.0.0.1") -> int:
    """Find an available ephemeral port on the specified host interface."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return s.getsockname()[1]


def hide_console_if_owned() -> None:
    """Hide the console window if this process was launched directly from Explorer or Start Menu.

    Checks if the process owns its own newly spawned console (via GetConsoleProcessList
    returning <= 2 processes). If so, hides the console window so no empty black window stays open,
    and redirects stdout and stderr to gui.log.
    """
    if sys.platform != "win32":
        return
    if "--debug-console" in sys.argv:
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32
        process_list = (ctypes.c_uint * 2)()
        count = kernel32.GetConsoleProcessList(process_list, 2)
        if count <= 2:
            hwnd = kernel32.GetConsoleWindow()
            if hwnd:
                user32.ShowWindow(hwnd, 0)
            setup_safe_stdio(force_redirect=True)
    except Exception:
        pass


def run_gui(browser: bool = False, port: Optional[int] = None) -> None:
    """Start local uvicorn server in a background thread and launch desktop window."""
    if not browser:
        hide_console_if_owned()
    setup_safe_stdio()
    if port is None:
        port = find_free_port("127.0.0.1")

    url = f"http://127.0.0.1:{port}"
    msg = f"lplab GUI server listening on {url}\n"
    if sys.stdout:
        sys.stdout.write(msg)
        sys.stdout.flush()
    try:
        with open(get_gui_log_path(), "a", encoding="utf-8") as f:
            f.write(msg)
    except Exception:
        pass

    from lplab.gui_server import app as fastapi_app

    config = uvicorn.Config(
        app=fastapi_app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        access_log=False,
        log_config=None,
    )
    server = uvicorn.Server(config)
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    # Wait until FastAPI server is ready and responds to /api/labs
    deadline = time.time() + 10.0
    ready = False
    while time.time() < deadline:
        try:
            req = urllib.request.Request(f"{url}/api/labs")
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    ready = True
                    break
        except Exception:
            time.sleep(0.1)

    if not ready:
        if sys.stderr:
            sys.stderr.write(f"Warning: Server at {url}/api/labs did not respond within timeout.\n")

    if browser:
        import webbrowser
        print(f"Opening lplab GUI in default browser: {url}")
        webbrowser.open(url)
        try:
            while server_thread.is_alive():
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            server.should_exit = True
            server_thread.join(timeout=2.0)
        return

    # Attempt native pywebview window launch
    try:
        import webview

        def on_closed():
            server.should_exit = True

        window = webview.create_window(
            title="lplab // CompTIA Linux+ XK0-006",
            url=url,
            width=1280,
            height=820,
            min_size=(960, 640),
        )
        window.events.closed += on_closed
        webview.start()
    except Exception as e:
        # Graceful fallback to default browser in headless / non-GUI environments
        import webbrowser
        if sys.stderr:
            sys.stderr.write(f"pywebview GUI window unavailable ({e}). Falling back to browser.\n")
        print(f"Opening lplab GUI in default browser: {url}")
        webbrowser.open(url)
        try:
            while server_thread.is_alive():
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
    finally:
        server.should_exit = True
        server_thread.join(timeout=2.0)


def main() -> None:
    """CLI entry point for direct execution (python -m lplab.gui)."""
    log_path = setup_safe_stdio()
    try:
        import argparse
        parser = argparse.ArgumentParser(description="lplab Native Desktop GUI")
        parser.add_argument(
            "--browser",
            action="store_true",
            help="Open in default web browser instead of pywebview window",
        )
        parser.add_argument(
            "--port",
            "-p",
            type=int,
            default=None,
            help="Port to bind (default: ephemeral free port)",
        )
        args = parser.parse_args()
        run_gui(browser=args.browser, port=args.port)
    except Exception as e:
        import traceback
        tb_str = traceback.format_exc()
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"\n--- GUI Startup Crash [{time.strftime('%Y-%m-%d %H:%M:%S')}] ---\n")
                f.write(tb_str)
        except Exception:
            pass
        if sys.stderr and sys.stderr is not sys.stdout:
            try:
                sys.stderr.write(tb_str)
            except Exception:
                pass
        if sys.platform == "win32":
            try:
                import ctypes
                MB_ICONERROR = 0x10
                MB_OK = 0x00
                msg = f"lplab GUI encountered an error during startup:\n\n{e}\n\nTraceback logged to:\n{log_path}"
                ctypes.windll.user32.MessageBoxW(0, msg, "lplab - Startup Error", MB_OK | MB_ICONERROR)
            except Exception:
                pass
        sys.exit(1)


if __name__ == "__main__":
    main()
