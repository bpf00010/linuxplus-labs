"""Tests for Pydantic v2 data models."""

import pytest
from pydantic import ValidationError

from lplab.models import (
    CheckResult,
    LabManifest,
    LabRuntimeStatus,
    LabStateRecord,
    VerifyReport,
)


def test_valid_lab_manifest():
    """Test creating a valid LabManifest."""
    manifest = LabManifest(
        id="lab-01",
        slug="lab-01-systemd-storage",
        title="Storage Recovery Lab",
        distro_name="lplab-lab-01",
        base_image="rockylinux-9",
        student_user="sysadmin",
        difficulty="intermediate",
        estimated_minutes=20,
        xk0_006_domains=["system_management", "troubleshooting"],
        objectives=["Mount /mnt/appdata", "Unmask service"],
    )
    assert manifest.id == "lab-01"
    assert manifest.distro_name == "lplab-lab-01"
    assert manifest.base_image == "rockylinux-9"
    assert manifest.difficulty == "intermediate"


def test_invalid_distro_namespace():
    """Test that distro_name without lplab- prefix raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        LabManifest(
            id="lab-test",
            slug="lab-test",
            title="Invalid Distro Name Test",
            distro_name="Ubuntu",  # Must be rejected!
            base_image="ubuntu-24.04",
        )
    assert "Strict Namespace Guard" in str(exc_info.value)

    with pytest.raises(ValidationError):
        LabManifest(
            id="lab-test",
            slug="lab-test",
            title="Invalid Distro Name Test",
            distro_name="my-distro",  # Must be rejected!
            base_image="ubuntu-24.04",
        )


def test_invalid_xk0_006_domain():
    """Test that invalid CompTIA domain raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        LabManifest(
            id="lab-test",
            slug="lab-test",
            title="Invalid Domain Test",
            distro_name="lplab-test",
            base_image="ubuntu-24.04",
            xk0_006_domains=["invalid_domain_name"],
        )
    assert "Invalid XK0-006 domain" in str(exc_info.value)


def test_verify_report_parsing():
    """Test parsing VerifyReport from valid JSON structure."""
    raw_json = {
        "lab_id": "lab-01",
        "passed": False,
        "score_passed": 1,
        "score_total": 3,
        "checks": [
            {
                "id": "chk-mount",
                "description": "Filesystem mounted",
                "passed": True,
                "details": "Mounted successfully",
            },
            {
                "id": "chk-service",
                "description": "Service active",
                "passed": False,
                "details": "Service is masked",
            },
            {
                "id": "chk-logrotate",
                "description": "Log under 5MB",
                "passed": False,
                "details": "File size 25MB",
            },
        ],
    }
    report = VerifyReport.model_validate(raw_json)
    assert report.lab_id == "lab-01"
    assert report.passed is False
    assert report.score_passed == 1
    assert report.score_total == 3
    assert len(report.checks) == 3
    assert report.checks[0].passed is True
    assert report.checks[1].passed is False


def test_lab_state_record():
    """Test state record persistence model."""
    record = LabStateRecord(
        lab_id="lab-02",
        distro_name="lplab-lab-02",
        status=LabRuntimeStatus.RUNNING,
    )
    assert record.status == LabRuntimeStatus.RUNNING
    record.status = LabRuntimeStatus.PASSED
    record.score_passed = 4
    record.score_total = 4
    record.checks = [
        CheckResult(id="chk-1", description="Test check", passed=True, details="OK")
    ]
    assert record.score_passed == 4
    assert len(record.checks) == 1
    assert record.checks[0].passed is True
