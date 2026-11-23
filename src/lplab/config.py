"""Configuration and state persistence management for lplab."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from lplab.models import AIConfig, AppConfig, CheckResult, LabRuntimeStatus, LabStateRecord
from lplab.paths import get_bundled_labs_dir, is_frozen


def find_project_root() -> Path:
    """Find the root directory of the linuxplus-labs project."""
    # Check current working directory or ancestors first if they contain labs/
    cwd = Path.cwd().resolve()
    for p in [cwd, *cwd.parents]:
        if (p / "labs").is_dir() or (p / "pyproject.toml").is_file():
            return p

    # Fall back to source tree root: src/lplab -> linuxplus-labs
    candidate = Path(__file__).resolve().parent.parent.parent
    if (candidate / "labs").is_dir() or (candidate / "pyproject.toml").is_file():
        return candidate

    return candidate


def get_default_storage_paths() -> tuple[Path, Path]:
    """Return (state_dir, distro_storage_dir) based on host platform."""
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data:
            try:
                creationflags = subprocess.CREATE_NO_WINDOW
                res = subprocess.run(
                    ["cmd.exe", "/c", "echo %LOCALAPPDATA%"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    creationflags=creationflags,
                )
                val = res.stdout.strip()
                if val and val != "%LOCALAPPDATA%":
                    local_app_data = val
            except Exception:
                pass
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

    distro_dir = base_dir / "distros"
    base_dir.mkdir(parents=True, exist_ok=True)
    distro_dir.mkdir(parents=True, exist_ok=True)
    return base_dir, distro_dir


def _expand_env_vars(data: Any) -> Any:
    """Recursively expand environment variables in strings."""
    if isinstance(data, str):
        return os.path.expandvars(data)
    if isinstance(data, dict):
        return {k: _expand_env_vars(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_expand_env_vars(item) for item in data]
    return data


def ensure_seed_labs_copied(bundled_labs_dir: Path, target_labs_dir: Path) -> None:
    """Copy missing seed lab directories from bundled read-only labs into target labs dir.

    Never overwrite existing labs in target_labs_dir to preserve user modifications and AI generated labs.
    """
    if not bundled_labs_dir.is_dir():
        return
    target_labs_dir.mkdir(parents=True, exist_ok=True)
    for item in bundled_labs_dir.iterdir():
        if item.is_dir() and ((item / "lab.yaml").is_file() or (item / "manifest.yaml").is_file()):
            dest_lab_dir = target_labs_dir / item.name
            if not dest_lab_dir.exists():
                shutil.copytree(item, dest_lab_dir)


def load_config(custom_config_path: Optional[Path] = None) -> AppConfig:
    """Load AppConfig, searching standard locations and applying defaults."""
    frozen = is_frozen()
    base_state_dir, distro_storage_dir = get_default_storage_paths()
    state_file = base_state_dir / "state.json"

    # Search for config.yaml
    candidate_paths: list[Path] = []
    if custom_config_path:
        candidate_paths.append(Path(custom_config_path).resolve())

    if frozen:
        candidate_paths.append(base_state_dir / "config.yaml")
    else:
        project_root = find_project_root()
        candidate_paths.append(project_root / "config.yaml")
        if sys.platform == "win32":
            candidate_paths.append(base_state_dir / "config.yaml")
        else:
            config_home = os.environ.get("XDG_CONFIG_HOME")
            default_cfg_dir = Path(config_home) / "lplab" if config_home else Path.home() / ".config" / "lplab"
            candidate_paths.append(default_cfg_dir / "config.yaml")

    loaded_cfg_file: Optional[Path] = None
    raw_config: Dict[str, Any] = {}
    for p in candidate_paths:
        if p.is_file():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    content = yaml.safe_load(f)
                    if isinstance(content, dict):
                        raw_config = _expand_env_vars(content)
                        loaded_cfg_file = p
                        break
            except Exception:
                pass

    if frozen:
        raw_labs = raw_config.get("labs_dir")
        labs_dir = Path(raw_labs) if raw_labs else (base_state_dir / "labs")

        raw_images = raw_config.get("base_images_dir")
        base_images_dir = Path(raw_images) if raw_images else (base_state_dir / "base-images")

        bundled_labs = get_bundled_labs_dir()
        ensure_seed_labs_copied(bundled_labs, labs_dir)
    else:
        project_root = find_project_root()
        pkg_root = Path(__file__).resolve().parent.parent.parent

        raw_labs = raw_config.get("labs_dir")
        if raw_labs:
            labs_dir = Path(raw_labs) if Path(raw_labs).is_absolute() else (project_root / raw_labs)
        else:
            labs_dir = project_root / "labs"
            if not labs_dir.is_dir() and (pkg_root / "labs").is_dir():
                labs_dir = pkg_root / "labs"

        raw_images = raw_config.get("base_images_dir")
        if raw_images:
            base_images_dir = Path(raw_images) if Path(raw_images).is_absolute() else (project_root / raw_images)
        else:
            base_images_dir = project_root / "base-images"
            if not base_images_dir.is_dir() and (pkg_root / "base-images").is_dir():
                base_images_dir = pkg_root / "base-images"

    labs_dir.mkdir(parents=True, exist_ok=True)
    base_images_dir.mkdir(parents=True, exist_ok=True)

    # Extract AI config
    ai_raw = raw_config.get("ai", {})
    ai_cfg = AIConfig(
        base_url=ai_raw.get("base_url", "http://localhost:11434/v1"),
        api_key=ai_raw.get("api_key", "ollama"),
        model=ai_raw.get("model", "llama3"),
    )

    custom_term = raw_config.get("custom_terminal_cmd")

    return AppConfig(
        labs_dir=labs_dir,
        base_images_dir=base_images_dir,
        distro_storage_dir=distro_storage_dir,
        state_file=state_file,
        config_file=loaded_cfg_file,
        custom_terminal_cmd=custom_term,
        ai=ai_cfg,
    )


def load_state(config: AppConfig) -> Dict[str, LabStateRecord]:
    """Load lab state records from state.json."""
    if not config.state_file.is_file():
        return {}
    try:
        with open(config.state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            records: Dict[str, LabStateRecord] = {}
            for k, v in data.items():
                records[k] = LabStateRecord.model_validate(v)
            return records
    except Exception:
        return {}


def save_state(config: AppConfig, state: Dict[str, LabStateRecord]) -> None:
    """Save lab state records to state.json atomically."""
    config.state_file.parent.mkdir(parents=True, exist_ok=True)
    temp_file = config.state_file.with_suffix(".tmp")
    data = {k: v.model_dump() for k, v in state.items()}
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    temp_file.replace(config.state_file)


def update_lab_state(
    config: AppConfig,
    lab_id: str,
    distro_name: str,
    status: Optional[LabRuntimeStatus] = None,
    last_verified: Optional[str] = None,
    score_passed: Optional[int] = None,
    score_total: Optional[int] = None,
    provisioned_at: Optional[str] = None,
    checks: Optional[List[CheckResult]] = None,
) -> LabStateRecord:
    """Update or create a state record for a lab."""
    current_state = load_state(config)
    record = current_state.get(
        lab_id,
        LabStateRecord(lab_id=lab_id, distro_name=distro_name)
    )
    record.distro_name = distro_name
    if status is not None:
        record.status = status
    if last_verified is not None:
        record.last_verified = last_verified
    if score_passed is not None:
        record.score_passed = score_passed
    if score_total is not None:
        record.score_total = score_total
    if provisioned_at is not None:
        record.provisioned_at = provisioned_at
    if checks is not None:
        record.checks = checks

    current_state[lab_id] = record
    save_state(config, current_state)
    return record
