"""Pydantic v2 data models for lplab."""

from enum import Enum
from pathlib import Path
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class LabRuntimeStatus(str, Enum):
    """Runtime lifecycle and verification status of a lab distro."""
    NOT_PROVISIONED = "NOT_PROVISIONED"
    STOPPED = "STOPPED"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"


VALID_XK0_006_DOMAINS = {
    "system_management",
    "services_and_users",
    "security",
    "automation_scripting",
    "troubleshooting",
}


class LabManifest(BaseModel):
    """Manifest describing a CompTIA Linux+ lab scenario."""
    id: str = Field(description="Unique lab identifier (e.g. lab-01)")
    slug: str = Field(description="URL and directory-safe slug (e.g. lab-01-systemd-storage)")
    title: str = Field(description="Human readable lab title")
    distro_name: str = Field(description="WSL2 distro name; MUST start with 'lplab-' prefix")
    base_image: Literal["rockylinux-9", "ubuntu-24.04"] = Field(
        default="rockylinux-9",
        description="Base image rootfs archive name"
    )
    student_user: str = Field(
        default="sysadmin",
        description="Non-root student username"
    )
    difficulty: Literal["beginner", "intermediate", "advanced"] = Field(
        default="intermediate",
        description="Difficulty rating"
    )
    estimated_minutes: int = Field(
        default=20,
        ge=5,
        le=180,
        description="Estimated time to complete in minutes"
    )
    xk0_006_domains: List[str] = Field(
        default_factory=list,
        description="CompTIA Linux+ XK0-006 exam objective domains"
    )
    objectives: List[str] = Field(
        default_factory=list,
        description="Specific behavioral objectives for this lab"
    )

    @field_validator("distro_name")
    @classmethod
    def validate_distro_namespace(cls, v: str) -> str:
        if not v.startswith("lplab-"):
            raise ValueError(
                f"Strict Namespace Guard: distro_name must start with 'lplab-', got '{v}'"
            )
        return v

    @field_validator("xk0_006_domains")
    @classmethod
    def validate_domains(cls, v: List[str]) -> List[str]:
        for d in v:
            if d not in VALID_XK0_006_DOMAINS:
                raise ValueError(
                    f"Invalid XK0-006 domain '{d}'. Must be one of: {sorted(VALID_XK0_006_DOMAINS)}"
                )
        return v


class CheckResult(BaseModel):
    """Result of an individual check in verify.sh."""
    id: str = Field(description="Check identifier")
    description: str = Field(description="Description of what was tested")
    passed: bool = Field(description="True if check passed")
    details: str = Field(default="", description="Diagnostic details or failure reasons")


class VerifyReport(BaseModel):
    """Report emitted by verify.sh adhering to strict JSON contract."""
    lab_id: str = Field(description="Lab ID")
    passed: bool = Field(description="Overall pass/fail state")
    score_passed: int = Field(ge=0, description="Count of passed checks")
    score_total: int = Field(ge=0, description="Total number of checks")
    checks: List[CheckResult] = Field(default_factory=list, description="List of check items")
    raw_output: Optional[str] = Field(default=None, description="Raw stdout/stderr if needed")


class AIConfig(BaseModel):
    """AI Generator connection settings."""
    base_url: str = Field(default="http://localhost:11434/v1", description="OpenAI-compatible API base URL")
    api_key: str = Field(default="ollama", description="API key (defaults to ollama)")
    model: str = Field(default="llama3", description="Model name")


class AppConfig(BaseModel):
    """Application global configuration."""
    labs_dir: Path = Field(description="Path to labs directory")
    base_images_dir: Path = Field(description="Path to cached base images (.tar)")
    distro_storage_dir: Path = Field(description="Path where WSL2 distro virtual disks are stored")
    state_file: Path = Field(description="Path to state.json persistence file")
    config_file: Optional[Path] = Field(default=None, description="Loaded config file if present")
    custom_terminal_cmd: Optional[str] = Field(default=None, description="Custom terminal launch command")
    ai: AIConfig = Field(default_factory=AIConfig, description="AI model configuration")


class LabStateRecord(BaseModel):
    """Persisted state for a specific lab scenario."""
    lab_id: str
    distro_name: str
    status: LabRuntimeStatus = LabRuntimeStatus.NOT_PROVISIONED
    last_verified: Optional[str] = None
    score_passed: int = 0
    score_total: int = 0
    provisioned_at: Optional[str] = None
    checks: List[CheckResult] = Field(
        default_factory=list,
        description="List of check items from last verification"
    )


class GeneratedLabPayload(BaseModel):
    """Payload produced by AI lab generator."""
    manifest: LabManifest
    brief_md: str
    setup_sh: str
    verify_sh: str
