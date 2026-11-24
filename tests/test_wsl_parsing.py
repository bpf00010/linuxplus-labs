"""Tests for WSL output decoding, table parsing, and strict namespace guards."""

from pathlib import Path
import pytest

from unittest.mock import MagicMock, patch

from lplab.wsl_manager import (
    decode_wsl_output,
    exec_in_distro,
    execute_script_stdin,
    import_distro,
    invalidate_distro_cache,
    list_distros,
    parse_wsl_list_output,
    terminate_distro,
    unregister_distro,
)


def test_decode_wsl_output_utf16le():
    """Test decoding UTF-16LE bytes with embedded null bytes from wsl.exe."""
    raw_utf16le = (
        "  NAME                   STATE           VERSION\r\n"
        "* Ubuntu                 Running         2\r\n"
        "  docker-desktop         Stopped         2\r\n"
        "  lplab-lab-01           Stopped         2\r\n"
    ).encode("utf-16-le")

    decoded = decode_wsl_output(raw_utf16le)
    assert "Ubuntu" in decoded
    assert "lplab-lab-01" in decoded
    # Verify default asterisk is stripped from beginning of line
    assert "* Ubuntu" not in decoded
    assert "\x00" not in decoded


def test_decode_wsl_output_utf8_fallback():
    """Test standard UTF-8 string decoding."""
    raw_utf8 = b"* Ubuntu                 Running         2\nlplab-lab-02           Running         2\n"
    decoded = decode_wsl_output(raw_utf8)
    assert "Ubuntu" in decoded
    assert "lplab-lab-02" in decoded
    assert decoded.splitlines()[0].startswith("Ubuntu")


def test_parse_wsl_list_output():
    """Test parsing tabular output into a clean dictionary."""
    sample_text = """
  NAME                   STATE           VERSION
* Ubuntu                 Running         2
  docker-desktop         Stopped         2
  lplab-lab-01-systemd   Stopped         2
  lplab-lab-02-firewall  Running         2
"""
    result = parse_wsl_list_output(sample_text)
    assert result == {
        "Ubuntu": "Running",
        "docker-desktop": "Stopped",
        "lplab-lab-01-systemd": "Stopped",
        "lplab-lab-02-firewall": "Running",
    }


def test_strict_namespace_guard_unregister():
    """Ensure unregister_distro raises ValueError for non-lplab distros."""
    with pytest.raises(ValueError) as exc:
        unregister_distro("Ubuntu")
    assert "Strict Namespace Guard" in str(exc.value)

    with pytest.raises(ValueError) as exc:
        unregister_distro("docker-desktop")
    assert "Strict Namespace Guard" in str(exc.value)

    with pytest.raises(ValueError) as exc:
        unregister_distro("Debian")
    assert "Strict Namespace Guard" in str(exc.value)


def test_strict_namespace_guard_terminate():
    """Ensure terminate_distro raises ValueError for non-lplab distros."""
    with pytest.raises(ValueError) as exc:
        terminate_distro("Ubuntu")
    assert "Strict Namespace Guard" in str(exc.value)


def test_strict_namespace_guard_import():
    """Ensure import_distro raises ValueError for non-lplab distros."""
    dummy_dir = Path("./dummy_dir")
    dummy_tar = Path("./dummy.tar")
    with pytest.raises(ValueError) as exc:
        import_distro("Ubuntu", dummy_dir, dummy_tar)
    assert "Strict Namespace Guard" in str(exc.value)


def test_crlf_normalization_in_exec_in_distro():
    """Verify CRLF \\r\\n line endings are converted to LF \\n before streaming."""
    script_with_crlf = "#!/bin/bash\r\necho hello\r\nexit 0\r\n"

    with patch("subprocess.run") as mock_run:
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = b"hello\n"
        mock_res.stderr = b""
        mock_run.return_value = mock_res

        rc, stdout, stderr = exec_in_distro("lplab-test", script_with_crlf)
        assert rc == 0
        assert mock_run.called

        # Extract input argument passed to subprocess.run
        _, kwargs = mock_run.call_args
        streamed_input = kwargs.get("input", b"")
        assert b"\r" not in streamed_input
        assert streamed_input == b"#!/bin/bash\necho hello\nexit 0\n"


def test_distro_cache_and_invalidation():
    """Verify list_distros uses 2.5s TTL cache and can be invalidated."""
    sample_raw = b"  NAME STATE VERSION\r\n* Ubuntu Running 2\r\n  lplab-test Running 2\r\n"

    with patch("subprocess.run") as mock_run:
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = sample_raw
        mock_res.stderr = b""
        mock_run.return_value = mock_res

        # Force refresh first call
        res1 = list_distros(force_refresh=True)
        assert "lplab-test" in res1
        assert mock_run.call_count == 1

        # Second call immediately should hit cache (call_count remains 1)
        res2 = list_distros()
        assert res2 == res1
        assert mock_run.call_count == 1

        # Invalidate cache
        invalidate_distro_cache()

        # Third call should call subprocess.run again (call_count becomes 2)
        res3 = list_distros()
        assert res3 == res1
        assert mock_run.call_count == 2


def test_wait_for_systemd_success():
    """Verify wait_for_systemd succeeds when PID 1 is systemd and status is running."""
    from lplab.wsl_manager import wait_for_systemd

    with patch("lplab.wsl_manager.execute_cmd") as mock_exec:
        mock_exec.side_effect = [
            (0, "systemd\n", ""),        # ps -p 1 -o comm=
            (0, "running\n", ""),        # systemctl is-system-running
        ]
        result = wait_for_systemd("lplab-test", timeout_s=5)
        assert result is True
        assert mock_exec.call_count == 2


def test_wait_for_systemd_retry_when_init():
    """Verify wait_for_systemd retries termination when PID 1 is initially init."""
    from lplab.wsl_manager import wait_for_systemd

    with patch("lplab.wsl_manager.execute_cmd") as mock_exec, \
         patch("lplab.wsl_manager.terminate_distro") as mock_term, \
         patch("time.sleep"):
        mock_exec.side_effect = [
            (0, "init\n", ""),           # initial check -> init
            (0, "systemd\n", ""),        # second check after cycle -> systemd
            (0, "degraded\n", ""),       # systemctl is-system-running -> degraded is acceptable
        ]
        result = wait_for_systemd("lplab-test", timeout_s=5)
        assert result is True
        assert mock_term.called
        assert mock_term.call_args[0][0] == "lplab-test"


def test_wait_for_systemd_raises_if_not_systemd():
    """Verify wait_for_systemd raises RuntimeError if PID 1 remains init."""
    from lplab.wsl_manager import wait_for_systemd

    with patch("lplab.wsl_manager.execute_cmd") as mock_exec, \
         patch("lplab.wsl_manager.terminate_distro"), \
         patch("time.sleep"):
        mock_exec.side_effect = [
            (0, "init\n", ""),
            (0, "init\n", ""),
        ]
        with pytest.raises(RuntimeError) as exc:
            wait_for_systemd("lplab-test", timeout_s=5)
        assert "failed to boot systemd as PID 1" in str(exc.value)


def test_wait_for_systemd_raises_on_timeout():
    """Verify wait_for_systemd raises RuntimeError when initialization times out."""
    from lplab.wsl_manager import wait_for_systemd

    def mock_cmd(distro, cmd, user="root", timeout=10):
        if "ps -p 1" in cmd:
            return (0, "systemd\n", "")
        return (1, "offline\n", "")

    current_time = [100.0]

    def mock_now():
        return current_time[0]

    def mock_sleep(s):
        current_time[0] += s

    with patch("lplab.wsl_manager.execute_cmd", side_effect=mock_cmd), \
         patch("time.time", side_effect=mock_now), \
         patch("time.sleep", side_effect=mock_sleep):
        with pytest.raises(RuntimeError) as exc:
            wait_for_systemd("lplab-test", timeout_s=5)
        assert "failed to initialize" in str(exc.value)


def test_configure_wsl_conf_writes_hardened_settings():
    """Verify configure_wsl_conf sets systemd=true, appendWindowsPath=false, and student user."""
    from lplab.wsl_manager import configure_wsl_conf

    with patch("lplab.wsl_manager.execute_cmd") as mock_exec:
        mock_exec.return_value = (0, "", "")
        configure_wsl_conf("lplab-test", "studentuser")

        assert mock_exec.called
        call_cmd = mock_exec.call_args[0][1]
        assert "systemd=true" in call_cmd
        assert "appendWindowsPath=false" in call_cmd
        assert "default=studentuser" in call_cmd

