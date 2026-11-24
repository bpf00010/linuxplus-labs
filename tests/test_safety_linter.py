"""Tests for the Static Safety Linter."""

from pathlib import Path
import pytest

from lplab.ai_generator import SafetyLinter
from lplab.models import GeneratedLabPayload, LabManifest


def test_reject_dangerous_rm():
    """Test that rm -rf / and variants are rejected."""
    dangerous_snippets = [
        "rm -rf /",
        "rm -rf /*",
        "rm -rf / *",
        "rm -r -f /",
        "rm -fr /",
        "rm --recursive --force /",
    ]
    for snippet in dangerous_snippets:
        errors = SafetyLinter.lint_script(snippet, "test.sh")
        assert any("destructive root command" in e for e in errors), f"Failed to reject: {snippet}"


def test_reject_host_mounts():
    """Test that /mnt/c or /mnt/d references are rejected."""
    bad_scripts = [
        "cp /mnt/c/Users/student/file.txt /etc/",
        "cat /mnt/d/backup.tar",
        "ls C:\\Users",
    ]
    for script in bad_scripts:
        errors = SafetyLinter.lint_script(script, "test.sh")
        assert any("host filesystem mount" in e for e in errors), f"Failed to reject: {script}"


def test_reject_unscoped_firewall_flush():
    """Test that unscoped global nft flush or iptables -F is rejected."""
    bad_flushes = [
        "nft flush ruleset",
        "iptables -F",
        "iptables --flush",
        "ip6tables -F",
    ]
    for cmd in bad_flushes:
        errors = SafetyLinter.lint_script(cmd, "test.sh")
        assert any("Global firewall flush detected" in e for e in errors), f"Failed to reject: {cmd}"


def test_accept_scoped_firewall_commands():
    """Test that scoped firewall commands (table inet lplab_...) are accepted."""
    safe_script = """#!/usr/bin/env bash
set -euo pipefail
nft delete table inet lplab02 2>/dev/null || true
nft add table inet lplab02
nft 'add chain inet lplab02 input { type filter hook input priority 0; policy accept; }'
nft add rule inet lplab02 input tcp dport 18080 drop
"""
    errors = SafetyLinter.lint_script(safe_script, "safe_firewall.sh")
    assert len(errors) == 0, f"False positive errors: {errors}"


def test_seed_labs_pass_linter():
    """Verify that all nine shipped seed labs pass the safety linter with zero errors."""
    labs_root = Path(__file__).resolve().parent.parent / "labs"

    seed_labs = [
        "lab-01-systemd-storage",
        "lab-02-networking-firewall",
        "lab-03-security-containers",
        "lab-04-systemd-timers-watchdog",
        "lab-05-netns-veth-routing",
        "lab-06-nginx-tls-port-conflict",
        "lab-07-ssh-pam-hardening",
        "lab-08-systemd-cgroups-sysctl",
        "lab-09-systemd-mount-resize",
    ]

    for lab_slug in seed_labs:
        lab_dir = labs_root / lab_slug
        assert lab_dir.is_dir(), f"Missing lab dir: {lab_dir}"

        setup_sh = (lab_dir / "setup.sh").read_text(encoding="utf-8")
        verify_sh = (lab_dir / "verify.sh").read_text(encoding="utf-8")

        setup_errors = SafetyLinter.lint_script(setup_sh, f"{lab_slug}/setup.sh")
        assert not setup_errors, f"{lab_slug} setup.sh errors: {setup_errors}"

        verify_errors = SafetyLinter.lint_script(verify_sh, f"{lab_slug}/verify.sh")
        assert not verify_errors, f"{lab_slug} verify.sh errors: {verify_errors}"

        json_contract_errors = SafetyLinter.lint_verify_script(verify_sh)
        assert not json_contract_errors, f"{lab_slug} verify.sh JSON errors: {json_contract_errors}"

        # Verify bash -n syntax checks pass for both scripts
        syntax_err_setup = SafetyLinter.check_bash_syntax(setup_sh)
        assert syntax_err_setup is None, f"{lab_slug}/setup.sh syntax error: {syntax_err_setup}"

        syntax_err_verify = SafetyLinter.check_bash_syntax(verify_sh)
        assert syntax_err_verify is None, f"{lab_slug}/verify.sh syntax error: {syntax_err_verify}"
