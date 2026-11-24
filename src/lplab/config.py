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

    Checks existing labs by ID (not just folder name) so upgrading lplab never creates duplicate IDs.
    If an existing directory has the same ID under an old superseded folder name, cleans up the old
    superseded directory and replaces it with the bundled version.
    """
    if not bundled_labs_dir.is_dir():
        return
    target_labs_dir.mkdir(parents=True, exist_ok=True)

    # Map existing target labs by ID
    existing_by_id: Dict[str, Path] = {}
    for sub in target_labs_dir.iterdir():
        if sub.is_dir():
            for m_name in ("lab.yaml", "manifest.yaml"):
                mf = sub / m_name
                if mf.is_file():
                    try:
                        with open(mf, "r", encoding="utf-8") as f:
                            data = yaml.safe_load(f)
                        if isinstance(data, dict) and "id" in data:
                            existing_by_id[str(data["id"])] = sub
                            break
                    except Exception:
                        pass

    for item in bundled_labs_dir.iterdir():
        if not item.is_dir():
            continue
        seed_manifest_file = item / "lab.yaml"
        if not seed_manifest_file.is_file():
            seed_manifest_file = item / "manifest.yaml"
        if not seed_manifest_file.is_file():
            continue

        seed_id: Optional[str] = None
        try:
            with open(seed_manifest_file, "r", encoding="utf-8") as f:
                seed_data = yaml.safe_load(f)
            if isinstance(seed_data, dict):
                seed_id = str(seed_data.get("id", ""))
        except Exception:
            pass

        dest_lab_dir = target_labs_dir / item.name
        if seed_id and seed_id in existing_by_id:
            old_dir = existing_by_id[seed_id]
            if old_dir.name != item.name:
                # Old superseded seed directory found with the same lab ID (e.g. lab-04-automation-timers)
                try:
                    shutil.rmtree(old_dir, ignore_errors=True)
                except Exception:
                    pass
                shutil.copytree(item, dest_lab_dir)
                existing_by_id[seed_id] = dest_lab_dir
            # Else already exists with matching ID and folder name; preserve user changes
        else:
            if not dest_lab_dir.exists():
                shutil.copytree(item, dest_lab_dir)
                if seed_id:
                    existing_by_id[seed_id] = dest_lab_dir


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
        provider=ai_raw.get("provider", "ollama"),
        base_url=ai_raw.get("base_url", "http://localhost:11434/v1"),
        model=ai_raw.get("model", "llama3"),
        api_key=ai_raw.get("api_key", "ollama"),
        api_key_env=ai_raw.get("api_key_env"),
        temperature=float(ai_raw.get("temperature", 0.2)),
        timeout_seconds=int(ai_raw.get("timeout_seconds", 180)),
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


def save_config(config: AppConfig, target_path: Optional[Path] = None) -> Path:
    """Persist AppConfig updates to config.yaml cleanly without overwriting unrelated fields."""
    dest = target_path or config.config_file
    if not dest:
        base_state_dir, _ = get_default_storage_paths()
        if is_frozen() or sys.platform == "win32":
            dest = base_state_dir / "config.yaml"
        else:
            dest = find_project_root() / "config.yaml"

    dest.parent.mkdir(parents=True, exist_ok=True)
    raw_data: Dict[str, Any] = {}
    if dest.is_file():
        try:
            with open(dest, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    raw_data = loaded
        except Exception:
            raw_data = {}

    ai_dict = config.ai.model_dump()
    raw_data["ai"] = ai_dict

    temp_file = dest.with_suffix(".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(raw_data, f, sort_keys=False, default_flow_style=False)
    temp_file.replace(dest)
    config.config_file = dest
    return dest

