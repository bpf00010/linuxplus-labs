"""Tests for the Static Safety Linter."""

from pathlib import Path
import pytest

from lplab.ai_generator import (
    SafetyLinter,
    assign_next_lab_id_and_distro,
    extract_json_from_response,
    strip_think_blocks,
)
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


def test_strip_think_blocks():
    """Verify strip_think_blocks removes thinking blocks across various formats."""
    # 1. Closed thinking block
    raw = "<think>\nThinking about how to design this lab...\n</think>\n```json\n{\"id\": \"lab-01\"}\n```"
    stripped = strip_think_blocks(raw)
    assert "<think>" not in stripped
    assert "Thinking about" not in stripped
    assert "```json" in stripped

    # 2. Case insensitive thinking block
    raw2 = "<THINK>internal reasoning</THINK>content"
    assert strip_think_blocks(raw2).strip() == "content"

    # 3. Unclosed thinking block at beginning
    raw3 = "<think>Still reasoning when context cut off\n\n```json\n{\"foo\": \"bar\"}\n```"
    # Unclosed think should truncate up to end or match correctly
    assert "<think>" not in strip_think_blocks(raw3)

    # 4. No think tags
    raw4 = "Just regular text"
    assert strip_think_blocks(raw4) == "Just regular text"


def test_extract_json_from_response():
    """Verify extract_json_from_response extracts payload even with think tags and markdown fences."""
    # Fenced JSON with leading think block
    resp = """<think>
Let's structure the JSON output according to schema.
</think>
Here is the lab configuration:
```json
{
  "manifest": {
    "title": "Configuring Nginx Reverse Proxy"
  },
  "brief_md": "# Ticket: Setup Nginx",
  "setup_sh": "#!/usr/bin/env bash\\necho ok",
  "verify_sh": "#!/usr/bin/env bash\\necho ok"
}
```
Hope this helps!"""
    data = extract_json_from_response(resp)
    assert isinstance(data, dict)
    assert data["manifest"]["title"] == "Configuring Nginx Reverse Proxy"
    assert data["brief_md"] == "# Ticket: Setup Nginx"

    # Raw JSON with whitespace and think tags
    resp_raw = """<think>done thinking</think>
{"manifest": {"title": "Raw JSON"}, "brief_md": "ticket", "setup_sh": "echo 1", "verify_sh": "echo 1"}"""
    data_raw = extract_json_from_response(resp_raw)
    assert data_raw["manifest"]["title"] == "Raw JSON"


def test_assign_next_lab_id_and_distro(tmp_path):
    """Verify non-colliding lab numbering and verify.sh lab_id replacement."""
    # Create fake existing labs lab-01 to lab-09 in tmp_path
    for i in range(1, 10):
        d = tmp_path / f"lab-0{i}-sample"
        d.mkdir()
        (d / "lab.yaml").write_text(f"id: lab-0{i}\nslug: lab-0{i}-sample\n", encoding="utf-8")

    manifest = LabManifest(
        id="lab-01",  # Colliding ID initially provided by LLM
        slug="storage-repair",
        title="Storage Repair",
        distro_name="lplab-lab-01",  # Colliding distro_name
        base_image="ubuntu-24.04",
        student_user="student",
        difficulty="intermediate",
        estimated_minutes=25,
        xk0_006_domains=["system_management"],
        objectives=["Fix fstab"],
    )

    verify_sh = """#!/usr/bin/env bash
cat << 'EOF'
{
  "lab_id": "lab-01",
  "passed": true
}
EOF
"""

    payload = GeneratedLabPayload(
        manifest=manifest,
        brief_md="# Brief",
        setup_sh="#!/bin/bash\necho setup",
        verify_sh=verify_sh,
    )

    updated = assign_next_lab_id_and_distro(payload, labs_dir=tmp_path)

    # Next available should be lab-10
    assert updated.manifest.id == "lab-10"
    assert updated.manifest.slug == "lab-10-storage-repair"
    assert updated.manifest.distro_name == "lplab-10"
    # verify.sh lab_id should be replaced
    assert '"lab_id": "lab-10"' in updated.verify_sh
    assert '"lab_id": "lab-01"' not in updated.verify_sh

