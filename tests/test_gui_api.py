"""Tests for FastAPI backend API and GUI launcher."""

import re
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from lplab.config import load_config
from lplab.gui_server import app, create_app
from lplab.lab_engine import LabEngine
from lplab.models import CheckResult, GeneratedLabPayload, LabManifest, LabRuntimeStatus, VerifyReport


@pytest.fixture
def client():
    """TestClient fixture bound to the GUI FastAPI app."""
    return TestClient(app)


def test_get_root_serves_html_dashboard_without_cdns(client):
    """Verify GET / returns HTTP 200 and serves self-contained HTML with zero external CDN scripts/styles."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"].lower()

    html = resp.text
    # App title present
    assert "lplab // CompTIA Linux+ XK0-006" in html
    assert "Launch Terminal" in html
    assert "Verify" in html

    # Strict Zero-CDN check: no external script tags or remote stylesheets
    external_scripts = re.findall(r'<script[^>]+src=["\'](https?://[^"\']+)["\']', html, re.IGNORECASE)
    assert external_scripts == [], f"Found disallowed external CDN scripts: {external_scripts}"

    external_links = re.findall(r'<link[^>]+href=["\'](https?://[^"\']+)["\']', html, re.IGNORECASE)
    assert external_links == [], f"Found disallowed external CDN styles/fonts: {external_links}"


def test_get_labs_returns_seed_labs(client):
    """Verify GET /api/labs returns all 9 seed labs with expected schema and runtime statuses."""
    resp = client.get("/api/labs")
    assert resp.status_code == 200
    labs = resp.json()
    assert isinstance(labs, list)
    assert len(labs) == 9

    lab_ids = [l["id"] for l in labs]
    for i in range(1, 10):
        expected_id = f"lab-0{i}"
        assert expected_id in lab_ids

    # Inspect lab-01 schema
    lab01 = next(l for l in labs if l["id"] == "lab-01")
    assert lab01["distro_name"] == "lplab-lab-01-systemd-storage"
    assert lab01["base_image"] == "rockylinux-9"
    assert "system_management" in lab01["xk0_006_domains"]
    assert lab01["status"] in [s.value for s in LabRuntimeStatus]
    assert "checks" in lab01


def test_get_lab_brief_returns_markdown_ticket(client):
    """Verify GET /api/labs/lab-01/brief returns the raw BRIEF.md work order and manifest."""
    resp = client.get("/api/labs/lab-01/brief")
    assert resp.status_code == 200
    data = resp.json()

    assert "manifest" in data
    assert data["manifest"]["id"] == "lab-01"
    assert "brief_md" in data
    # Check ticket content
    assert "TICKET-8921" in data["brief_md"]
    assert "Incident Summary" in data["brief_md"]

    # Verify 404 for unknown lab
    resp_404 = client.get("/api/labs/non-existent-lab-xyz/brief")
    assert resp_404.status_code == 404


def test_post_start_invokes_mocked_lab_engine(client):
    """Verify POST /api/labs/lab-01/start invokes engine.start_lab cleanly."""
    with patch.object(app.state.engine, "start_lab") as mock_start:
        resp = client.post("/api/labs/lab-01/start")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["lab_id"] == "lab-01"
        assert mock_start.called
        # Check call args
        args, kwargs = mock_start.call_args
        manifest = kwargs.get("manifest") or args[0]
        assert manifest.id == "lab-01"


def test_post_verify_invokes_mocked_lab_engine(client):
    """Verify POST /api/labs/lab-01/verify invokes engine.verify_lab and returns full VerifyReport JSON."""
    dummy_report = VerifyReport(
        lab_id="lab-01",
        passed=True,
        score_passed=3,
        score_total=3,
        checks=[
            CheckResult(id="chk-mount", description="Storage mount active", passed=True, details="/mnt/appdata mounted"),
            CheckResult(id="chk-service", description="Service active", passed=True, details="running"),
            CheckResult(id="chk-logrotate", description="Log rotation active", passed=True, details="size under 5MB"),
        ],
        raw_output="All checks passed.",
    )

    with patch.object(app.state.engine, "verify_lab", return_value=dummy_report) as mock_verify:
        resp = client.post("/api/labs/lab-01/verify")
        assert resp.status_code == 200
        data = resp.json()

        assert data["lab_id"] == "lab-01"
        assert data["passed"] is True
        assert data["score_passed"] == 3
        assert data["score_total"] == 3
        assert len(data["checks"]) == 3
        assert data["checks"][0]["id"] == "chk-mount"
        assert mock_verify.called


def test_post_stop_and_reset_invokes_mocked_lab_engine(client):
    """Verify POST stop and reset routes cleanly call engine methods."""
    with patch.object(app.state.engine, "stop_lab") as mock_stop:
        resp = client.post("/api/labs/lab-01/stop")
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"
        assert mock_stop.called

    with patch.object(app.state.engine, "reset_lab") as mock_reset:
        resp = client.post("/api/labs/lab-01/reset")
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"
        assert mock_reset.called


def test_images_status_and_build(client):
    """Verify GET /api/images/status and POST /api/images/build."""
    resp = client.get("/api/images/status")
    assert resp.status_code == 200
    status_data = resp.json()
    assert "rockylinux-9" in status_data
    assert "ubuntu-24.04" in status_data

    with patch("lplab.gui_server.build_rootfs_tar", return_value=Path("mock.tar")) as mock_build:
        resp_build = client.post("/api/images/build", json={"image": "rockylinux-9", "force": False})
        assert resp_build.status_code == 200
        assert resp_build.json()["status"] == "success"
        assert mock_build.called


def test_generate_api(client, tmp_path):
    """Verify POST /api/generate invokes AILabGenerator and returns metadata."""
    dummy_manifest = LabManifest(
        id="lab-99",
        slug="lab-99-test-gen",
        title="Test Generated Lab",
        distro_name="lplab-lab-99-test-gen",
        base_image="rockylinux-9",
        student_user="sysadmin",
        difficulty="beginner",
        estimated_minutes=15,
        xk0_006_domains=["system_management"],
        objectives=["Test objective"],
    )
    dummy_payload = GeneratedLabPayload(
        manifest=dummy_manifest,
        brief_md="# Test Brief",
        setup_sh="#!/bin/bash\necho setup",
        verify_sh="#!/bin/bash\necho verify",
    )

    with patch("lplab.gui_server.AILabGenerator") as mock_gen_cls:
        mock_instance = mock_gen_cls.return_value
        mock_instance.generate_lab.return_value = dummy_payload
        mock_instance.save_generated_lab.return_value = tmp_path / "lab-99-test-gen"

        resp = client.post(
            "/api/generate",
            json={
                "domain": "system_management",
                "topic": "storage-repair",
                "base_image": "rockylinux-9",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["manifest"]["id"] == "lab-99"
        assert mock_instance.generate_lab.called


def test_gui_safe_stdio_and_windowless_startup(monkeypatch, tmp_path):
    """Verify gui.py handles sys.stdout=None and sys.stderr=None cleanly without uvicorn crashing."""
    import sys
    import uvicorn
    from lplab.gui import get_gui_log_path, setup_safe_stdio

    # Mock LOCALAPPDATA to point to isolated tmp_path
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)

    log_path = setup_safe_stdio()
    assert log_path.parent == tmp_path / "linuxplus-labs"
    assert sys.stdout is not None
    assert sys.stderr is not None

    # Write test output to verify streams are functional
    sys.stdout.write("stdout test message\n")
    sys.stderr.write("stderr test message\n")
    if hasattr(sys.stdout, "flush"):
        sys.stdout.flush()
    if hasattr(sys.stderr, "flush"):
        sys.stderr.flush()

    assert log_path.is_file()
    content = log_path.read_text(encoding="utf-8")
    assert "stdout test message" in content
    assert "stderr test message" in content

    # Verify uvicorn.Config initializes cleanly with log_config=None under redirected/None stdio
    cfg = uvicorn.Config(
        app="lplab.gui_server:app",
        host="127.0.0.1",
        port=9999,
        log_level="warning",
        access_log=False,
        log_config=None,
    )
    server = uvicorn.Server(cfg)
    assert server.config.log_config is None


def test_frozen_path_resolution_and_seed_lab_copy(monkeypatch, tmp_path):
    """Verify frozen path resolution and automatic seed lab copying to user AppData."""
    import sys
    from lplab.config import ensure_seed_labs_copied, load_config
    from lplab.paths import get_bundle_dir, get_bundled_labs_dir, get_static_index_path, is_frozen

    # 1. Test source mode path resolution
    assert is_frozen() is False
    assert get_bundle_dir().is_dir()
    assert get_static_index_path().is_file()
    assert get_bundled_labs_dir().is_dir()

    # 2. Simulate frozen executable environment
    fake_meipass = tmp_path / "meipass"
    fake_meipass.mkdir()
    fake_bundled_labs = fake_meipass / "labs"
    fake_bundled_labs.mkdir()

    lab1 = fake_bundled_labs / "lab-seed-01"
    lab1.mkdir()
    (lab1 / "lab.yaml").write_text("id: lab-seed-01\n", encoding="utf-8")
    (lab1 / "BRIEF.md").write_text("# Seed 1\n", encoding="utf-8")

    fake_static = fake_meipass / "lplab" / "static"
    fake_static.mkdir(parents=True)
    (fake_static / "index.html").write_text("<html>Frozen</html>", encoding="utf-8")

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(fake_meipass), raising=False)

    assert is_frozen() is True
    assert get_bundle_dir() == fake_meipass
    assert get_static_index_path() == fake_static / "index.html"
    assert get_bundled_labs_dir() == fake_bundled_labs

    # 3. Test ensure_seed_labs_copied non-overwrite semantics
    target_labs = tmp_path / "appdata" / "labs"
    target_labs.mkdir(parents=True)

    existing_lab = target_labs / "lab-seed-01"
    existing_lab.mkdir()
    (existing_lab / "lab.yaml").write_text("id: lab-seed-01\nmodified: true\n", encoding="utf-8")

    lab2 = fake_bundled_labs / "lab-seed-02"
    lab2.mkdir()
    (lab2 / "lab.yaml").write_text("id: lab-seed-02\n", encoding="utf-8")

    ensure_seed_labs_copied(fake_bundled_labs, target_labs)

    assert "modified: true" in (existing_lab / "lab.yaml").read_text(encoding="utf-8")
    assert (target_labs / "lab-seed-02" / "lab.yaml").is_file()

    # 4. Test load_config in frozen mode uses AppData and copies missing labs
    appdata_dir = tmp_path / "appdata_local"
    monkeypatch.setenv("LOCALAPPDATA", str(appdata_dir))
    cfg = load_config()
    assert cfg.labs_dir == appdata_dir / "linuxplus-labs" / "labs"
    assert cfg.base_images_dir == appdata_dir / "linuxplus-labs" / "base-images"
    assert (cfg.labs_dir / "lab-seed-01" / "lab.yaml").is_file()
    assert (cfg.labs_dir / "lab-seed-02" / "lab.yaml").is_file()


