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
