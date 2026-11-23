"""WSL2 process management, output decoding, distro provisioning, and execution."""

import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

_SUBPROCESS_KWARGS: Dict[str, Any] = (
    {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}
)


def decode_wsl_output(raw: bytes | str) -> str:
    """Decode raw output from wsl.exe, handling UTF-16LE, BOM, and null byte artifacts.

    WSL.exe on Windows typically emits UTF-16LE text with embedded null bytes when
    interpreted as ASCII/UTF-8. This decoder reliably normalizes it to clean UTF-8 string.
    """
    if isinstance(raw, str):
        text = raw
    elif not raw:
        return ""
    else:
        # Check if raw bytes contain UTF-16 indicators (BOM or null bytes typical of UTF-16LE ASCII)
        if raw.startswith(b"\xff\xfe") or b"\x00" in raw:
            try:
                decoded = raw.decode("utf-16-le", errors="replace").replace("\x00", "")
            except Exception:
                decoded = raw.replace(b"\x00", b"").decode("utf-8", errors="replace")
        else:
            decoded = raw.decode("utf-8", errors="replace")

        text = decoded

    # Strip carriage returns and normalize newlines
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        # Strip default distro asterisk marker (e.g. '* Ubuntu' -> 'Ubuntu')
        if stripped.startswith("*"):
            stripped = stripped[1:].strip()
        cleaned_lines.append(stripped)

    return "\n".join(cleaned_lines)


def parse_wsl_list_output(output: str) -> Dict[str, str]:
    """Parse output of `wsl.exe --list --verbose` into a dict of {distro_name: state}.

    Example input lines:
      NAME            STATE           VERSION
    * Ubuntu          Running         2
      lplab-lab-01    Stopped         2
    """
    distros: Dict[str, str] = {}
    lines = output.splitlines()

    for line in lines:
        cleaned = line.strip()
        if not cleaned:
            continue
        # Strip leading * marker
        if cleaned.startswith("*"):
            cleaned = cleaned[1:].strip()

        # Split on multiple whitespace
        tokens = re.split(r"\s{2,}|\t+", cleaned)
        if len(tokens) >= 2:
            name = tokens[0].strip()
            state = tokens[1].strip()
            # Ignore table headers
            if name.upper() in ("NAME", "DISTRO") or state.upper() in ("STATE", "VERSION"):
                continue
            if name:
                distros[name] = state.capitalize()
        elif len(tokens) == 1:
            # Sometimes single space delimited
            parts = cleaned.split()
            if len(parts) >= 2 and parts[0].upper() not in ("NAME", "DISTRO"):
                name = parts[0].strip()
                state = parts[1].strip()
                distros[name] = state.capitalize()

    return distros


def to_windows_path(path: Path | str) -> str:
    """Translate path to a native Windows path suitable for wsl.exe arguments.

    If running on Windows Python: returns resolved native Windows path.
    If running inside Linux WSL: calls `wslpath -w` to get the Windows path.
    """
    p_str = str(path)
    if sys.platform == "win32":
        return str(Path(path).resolve())
    else:
        try:
            res = subprocess.run(
                ["wslpath", "-w", p_str],
                capture_output=True,
                text=True,
                check=True,
                **_SUBPROCESS_KWARGS,
            )
            return res.stdout.strip()
        except Exception:
            return p_str


def get_wsl_cmd() -> str:
    """Return command name or path for wsl.exe."""
    return "wsl.exe"


_DISTRO_CACHE: Dict[str, str] = {}
_DISTRO_CACHE_TIMESTAMP: float = 0.0
DISTRO_CACHE_TTL: float = 2.5


def invalidate_distro_cache() -> None:
    """Invalidate the in-memory distro status cache."""
    global _DISTRO_CACHE_TIMESTAMP
    _DISTRO_CACHE_TIMESTAMP = 0.0


def list_distros(force_refresh: bool = False) -> Dict[str, str]:
    """Return dictionary of {distro_name: state} from wsl.exe --list --verbose with 2.5s TTL cache."""
    global _DISTRO_CACHE, _DISTRO_CACHE_TIMESTAMP
    now = time.time()
    if not force_refresh and (now - _DISTRO_CACHE_TIMESTAMP < DISTRO_CACHE_TTL):
        return dict(_DISTRO_CACHE)

    try:
        res = subprocess.run(
            [get_wsl_cmd(), "--list", "--verbose"],
            capture_output=True,
            timeout=10,
            **_SUBPROCESS_KWARGS,
        )
        decoded = decode_wsl_output(res.stdout)
        _DISTRO_CACHE = parse_wsl_list_output(decoded)
        _DISTRO_CACHE_TIMESTAMP = now
        return dict(_DISTRO_CACHE)
    except Exception:
        return dict(_DISTRO_CACHE)


def is_distro_registered(distro_name: str) -> bool:
    """Check if distro is currently imported/registered in WSL."""
    distros = list_distros()
    return distro_name in distros


def is_distro_running(distro_name: str) -> bool:
    """Check if distro is currently running."""
    distros = list_distros()
    state = distros.get(distro_name, "")
    return state.lower() == "running"


def terminate_distro(distro_name: str) -> None:
    """Terminate running distro with strict namespace check."""
    if not distro_name.startswith("lplab-"):
        raise ValueError(
            f"Strict Namespace Guard: Cannot terminate '{distro_name}'. "
            f"Distro name must start with 'lplab-' prefix to prevent touching user distros."
        )
    subprocess.run(
        [get_wsl_cmd(), "--terminate", distro_name],
        capture_output=True,
        timeout=15,
        check=False,
        **_SUBPROCESS_KWARGS,
    )
    invalidate_distro_cache()


def unregister_distro(distro_name: str) -> None:
    """Unregister distro with strict namespace check."""
    if not distro_name.startswith("lplab-"):
        raise ValueError(
            f"Strict Namespace Guard: Cannot unregister '{distro_name}'. "
            f"Distro name must start with 'lplab-' prefix to prevent touching user distros."
        )
    subprocess.run(
        [get_wsl_cmd(), "--unregister", distro_name],
        capture_output=True,
        timeout=20,
        check=False,
        **_SUBPROCESS_KWARGS,
    )
    invalidate_distro_cache()


def import_distro(
    distro_name: str,
    install_dir: Path,
    rootfs_tar_path: Path,
) -> None:
    """Import a rootfs tarball as a new WSL2 distro with strict namespace check."""
    if not distro_name.startswith("lplab-"):
        raise ValueError(
            f"Strict Namespace Guard: Cannot import '{distro_name}'. "
            f"Distro name must start with 'lplab-' prefix to prevent touching user distros."
        )

    install_dir.mkdir(parents=True, exist_ok=True)
    win_install_dir = to_windows_path(install_dir)
    win_tar_path = to_windows_path(rootfs_tar_path)

    cmd = [
        get_wsl_cmd(),
        "--import",
        distro_name,
        win_install_dir,
        win_tar_path,
        "--version",
        "2",
    ]

    res = subprocess.run(cmd, capture_output=True, timeout=120, **_SUBPROCESS_KWARGS)
    if res.returncode != 0:
        err_msg = decode_wsl_output(res.stderr or res.stdout)
        raise RuntimeError(f"Failed to import distro '{distro_name}': {err_msg}")
    invalidate_distro_cache()


def execute_cmd(
    distro_name: str,
    command: str,
    user: str = "root",
    timeout: int = 60,
) -> Tuple[int, str, str]:
    """Execute command inside distro via wsl.exe -d <distro> -u <user> -- <command>."""
    cmd = [get_wsl_cmd(), "-d", distro_name, "-u", user, "--", "bash", "-c", command]
    try:
        res = subprocess.run(cmd, capture_output=True, timeout=timeout, **_SUBPROCESS_KWARGS)
        stdout = decode_wsl_output(res.stdout)
        stderr = decode_wsl_output(res.stderr)
        return res.returncode, stdout, stderr
    except subprocess.TimeoutExpired as e:
        stdout = decode_wsl_output(e.stdout) if e.stdout else ""
        stderr = decode_wsl_output(e.stderr) if e.stderr else "command timed out"
        return -1, stdout, stderr


def execute_script_stdin(
    distro_name: str,
    script_content: str,
    user: str = "root",
    timeout: int = 120,
) -> Tuple[int, str, str]:
    """Execute bash script by streaming over stdin (wsl.exe -d <distro> -u <user> -- bash -s).

    Ensures zero reliance on host-side mount paths like /mnt/c.
    Normalizes CRLF to LF to prevent $'\\r': command not found errors inside Linux.
    """
    normalized_content = script_content.replace("\r\n", "\n").replace("\r", "\n")
    cmd = [get_wsl_cmd(), "-d", distro_name, "-u", user, "--", "bash", "-s"]
    res = subprocess.run(
        cmd,
        input=normalized_content.encode("utf-8"),
        capture_output=True,
        timeout=timeout,
        **_SUBPROCESS_KWARGS,
    )
    # verify.sh or setup.sh output
    stdout = decode_wsl_output(res.stdout)
    stderr = decode_wsl_output(res.stderr)
    return res.returncode, stdout, stderr


# Convenient alias
exec_in_distro = execute_script_stdin


def configure_wsl_conf(distro_name: str, student_user: str) -> None:
    """Configure /etc/wsl.conf inside distro with systemd enabled and interop path append disabled."""
    wsl_conf = f"""[boot]
systemd=true

[automount]
enabled=false

[interop]
enabled=false
appendWindowsPath=false

[user]
default={student_user}
"""
    write_conf_cmd = f"cat <<'EOF' > /etc/wsl.conf\n{wsl_conf}\nEOF\nchmod 644 /etc/wsl.conf"
    rc, out, err = execute_cmd(distro_name, write_conf_cmd, user="root")
    if rc != 0:
        raise RuntimeError(f"Failed to write /etc/wsl.conf: {err or out}")


def provision_distro(
    distro_name: str,
    install_dir: Path,
    rootfs_tar_path: Path,
    student_user: str,
    setup_script: str,
    brief_markdown: str,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> None:
    """Execute the mandatory 6-step systemd activation & provisioning cycle."""
    def log(msg: str) -> None:
        if progress_callback:
            progress_callback(msg)

    # 1. Import distro
    log(f"[1/6] Importing WSL2 distro '{distro_name}' from {rootfs_tar_path.name}...")
    import_distro(distro_name, install_dir, rootfs_tar_path)

    # 2. Create non-root student user
    log(f"[2/6] Configuring student user '{student_user}'...")
    create_user_cmd = (
        f"id -u {student_user} &>/dev/null || ("
        f"useradd -m -s /bin/bash {student_user} && "
        f"echo '{student_user}:linuxplus' | chpasswd && "
        f"(usermod -aG wheel {student_user} 2>/dev/null || usermod -aG sudo {student_user} 2>/dev/null || true)"
        f")"
    )
    rc, out, err = execute_cmd(distro_name, create_user_cmd, user="root")
    if rc != 0:
        raise RuntimeError(f"Failed to create user '{student_user}': {err or out}")

    # 3. Write /etc/wsl.conf
    log("[3/6] Setting up /etc/wsl.conf (systemd=true, no host mounts/interop)...")
    configure_wsl_conf(distro_name, student_user)

    # 4. Terminate distro
    log(f"[4/6] Cycling WSL instance to activate systemd...")
    terminate_distro(distro_name)
    time.sleep(2)

    # 5. Boot and poll systemctl is-system-running (45s timeout)
    log("[5/6] Booting distro and waiting for systemd initialization...")
    start_time = time.time()
    systemd_ready = False
    last_status = "unknown"
    while time.time() - start_time < 45:
        rc, out, _ = execute_cmd(
            distro_name,
            "systemctl is-system-running 2>&1",
            user="root",
            timeout=10,
        )
        status_lines = [line.strip().lower() for line in out.splitlines() if line.strip()]
        last_status = status_lines[-1] if status_lines else "unknown"
        if any(s in ("running", "degraded") for s in status_lines):
            systemd_ready = True
            break
        time.sleep(2)

    if not systemd_ready:
        log(f"Warning: systemd state after timeout: '{last_status}'. Continuing...")

    # 6. Execute setup.sh via stdin & install BRIEF.md (chmod 444)
    log("[6/6] Executing lab setup script and deploying BRIEF.md...")
    # Deploy BRIEF.md to student home directory
    brief_deploy_script = f"""mkdir -p /home/{student_user}
cat <<'EOF' > /home/{student_user}/BRIEF.md
{brief_markdown}
EOF
chown {student_user}:{student_user} /home/{student_user}/BRIEF.md 2>/dev/null || true
chmod 444 /home/{student_user}/BRIEF.md
"""
    rc, out, err = execute_script_stdin(distro_name, brief_deploy_script, user="root")
    if rc != 0:
        log(f"Warning: Failed to write BRIEF.md: {err}")

    # Execute setup.sh
    rc, out, err = execute_script_stdin(distro_name, setup_script, user="root", timeout=180)
    if rc != 0:
        raise RuntimeError(f"setup.sh failed with exit code {rc}:\n{err or out}")

    log(f"Distro '{distro_name}' provisioned successfully.")


def launch_terminal(
    distro_name: str,
    student_user: str,
    title: str,
    custom_cmd_template: Optional[str] = None,
) -> None:
    """Launch interactive terminal attached to distro as student_user."""
    invalidate_distro_cache()
    if custom_cmd_template:
        cmd_str = custom_cmd_template.format(
            distro=distro_name,
            user=student_user,
            title=title,
        )
        subprocess.Popen(cmd_str, shell=True)
        return

    if sys.platform == "win32":
        # Prefer Windows Terminal (wt.exe)
        wt_path = shutil.which("wt.exe") or shutil.which("wt")
        if wt_path:
            try:
                cmd = [
                    wt_path,
                    "-w",
                    "0",
                    "new-tab",
                    "--title",
                    title,
                    "--",
                    "wsl.exe",
                    "-d",
                    distro_name,
                    "-u",
                    student_user,
                ]
                subprocess.Popen(cmd)
                return
            except Exception:
                pass

        # Fallback to cmd.exe /c start wsl.exe
        subprocess.Popen(
            f'cmd.exe /c start "{title}" wsl.exe -d {distro_name} -u {student_user}',
            shell=True,
        )
    else:
        # Running inside Linux WSL or Linux host
        subprocess.Popen(
            [get_wsl_cmd(), "-d", distro_name, "-u", student_user]
        )
