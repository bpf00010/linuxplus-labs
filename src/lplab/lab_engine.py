"""Core lab orchestration engine for discovery, provisioning, verification, and reset."""

from datetime import datetime
import json
import logging
import re
import shutil
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple
import yaml

from lplab.config import AppConfig, load_state, update_lab_state
from lplab.models import (
    CheckResult,
    LabManifest,
    LabRuntimeStatus,
    LabStateRecord,
    VerifyReport,
)
import lplab.wsl_manager as wsl_mgr

logger = logging.getLogger("lplab.lab_engine")


class LabEngine:
    """Orchestrator for managing the lifecycle of CompTIA Linux+ WSL labs."""

    def __init__(self, config: AppConfig):
        self.config = config

    def discover_labs(self) -> List[Tuple[LabManifest, Path]]:
        """Discover all valid lab scenarios in config.labs_dir, deduplicating strictly by manifest.id."""
        labs: List[Tuple[LabManifest, Path]] = []
        if not self.config.labs_dir.is_dir():
            return labs

        seen_ids: set[str] = set()
        for sub in sorted(self.config.labs_dir.iterdir()):
            if not sub.is_dir():
                continue
            manifest_file = sub / "lab.yaml"
            if manifest_file.is_file():
                try:
                    with open(manifest_file, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                    manifest = LabManifest.model_validate(data)
                    if manifest.id in seen_ids:
                        logger.warning(
                            f"Duplicate lab ID '{manifest.id}' found in '{sub}'. Skipping duplicate entry."
                        )
                        continue
                    seen_ids.add(manifest.id)
                    labs.append((manifest, sub))
                except Exception as e:
                    # Ignore malformed directories or log
                    pass
        return labs

    def get_lab(self, lab_id_or_slug: str) -> Optional[Tuple[LabManifest, Path]]:
        """Look up a single lab by its id (e.g. 'lab-01') or slug (e.g. 'lab-01-systemd-storage')."""
        for manifest, path in self.discover_labs():
            if manifest.id == lab_id_or_slug or manifest.slug == lab_id_or_slug:
                return manifest, path
        return None

    def get_lab_status(self, manifest: LabManifest) -> Tuple[LabRuntimeStatus, Optional[LabStateRecord]]:
        """Determine current runtime and verification status of a lab."""
        state_map = load_state(self.config)
        record = state_map.get(manifest.id)

        # Query live WSL distros
        live_distros = wsl_mgr.list_distros()
        is_registered = manifest.distro_name in live_distros

        if not is_registered:
            return LabRuntimeStatus.NOT_PROVISIONED, record

        is_running = live_distros.get(manifest.distro_name, "").lower() == "running"

        if record:
            if record.status in (LabRuntimeStatus.PASSED, LabRuntimeStatus.FAILED):
                return record.status, record

        if is_running:
            return LabRuntimeStatus.RUNNING, record
        else:
            return LabRuntimeStatus.STOPPED, record

    def provision_lab(
        self,
        manifest: LabManifest,
        lab_dir: Path,
        force: bool = False,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Provision the WSL2 distro for the lab following the 6-step cycle."""
        def log(msg: str) -> None:
            if progress_callback:
                progress_callback(msg)

        # Check if already registered
        if wsl_mgr.is_distro_registered(manifest.distro_name):
            if not force:
                log(f"Distro '{manifest.distro_name}' is already provisioned.")
                return
            log(f"Force re-provisioning: removing existing distro '{manifest.distro_name}'...")
            self.stop_lab(manifest, progress_callback=progress_callback)
            wsl_mgr.unregister_distro(manifest.distro_name)

        # Verify base image archive exists
        tar_path = self.config.base_images_dir / f"{manifest.base_image}.tar"
        if not tar_path.is_file():
            raise FileNotFoundError(
                f"Base image archive '{tar_path.name}' not found at {tar_path}.\n"
                f"Please run 'lplab build-image {manifest.base_image}' first."
            )

        # Read setup.sh and BRIEF.md
        setup_file = lab_dir / "setup.sh"
        if not setup_file.is_file():
            raise FileNotFoundError(f"Missing setup script at {setup_file}")
        setup_script = setup_file.read_text(encoding="utf-8")

        brief_file = lab_dir / "BRIEF.md"
        brief_md = brief_file.read_text(encoding="utf-8") if brief_file.is_file() else ""

        install_dir = self.config.distro_storage_dir / manifest.distro_name
        if install_dir.exists():
            shutil.rmtree(install_dir, ignore_errors=True)
        install_dir.mkdir(parents=True, exist_ok=True)

        wsl_mgr.provision_distro(
            distro_name=manifest.distro_name,
            install_dir=install_dir,
            rootfs_tar_path=tar_path,
            student_user=manifest.student_user,
            setup_script=setup_script,
            brief_markdown=brief_md,
            progress_callback=progress_callback,
        )

        # Sanity assertion: systemctl is-system-running must respond and not be offline
        rc, out, _ = wsl_mgr.execute_cmd(manifest.distro_name, "systemctl is-system-running 2>&1", user="root")
        if "offline" in out.lower():
            raise RuntimeError(
                f"Distro '{manifest.distro_name}' systemd manager is offline after setup: {out}"
            )

        update_lab_state(
            self.config,
            lab_id=manifest.id,
            distro_name=manifest.distro_name,
            status=LabRuntimeStatus.STOPPED,
            provisioned_at=datetime.now().isoformat(),
        )

    def start_lab(
        self,
        manifest: LabManifest,
        lab_dir: Path,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Ensure lab is provisioned, boot it, and launch user terminal."""
        def log(msg: str) -> None:
            if progress_callback:
                progress_callback(msg)

        if not wsl_mgr.is_distro_registered(manifest.distro_name):
            log(f"Lab '{manifest.id}' is not yet provisioned. Initiating provisioning...")
            self.provision_lab(manifest, lab_dir, progress_callback=progress_callback)

        log(f"Launching terminal for '{manifest.title}' ({manifest.distro_name})...")
        wsl_mgr.launch_terminal(
            distro_name=manifest.distro_name,
            student_user=manifest.student_user,
            title=f"Linux+ Lab: {manifest.title}",
            custom_cmd_template=self.config.custom_terminal_cmd,
        )

        update_lab_state(
            self.config,
            lab_id=manifest.id,
            distro_name=manifest.distro_name,
            status=LabRuntimeStatus.RUNNING,
        )

    def verify_lab(
        self,
        manifest: LabManifest,
        lab_dir: Path,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> VerifyReport:
        """Run non-destructive verify.sh via stdin and parse strict JSON report."""
        def log(msg: str) -> None:
            if progress_callback:
                progress_callback(msg)

        if not wsl_mgr.is_distro_registered(manifest.distro_name):
            raise RuntimeError(
                f"Cannot verify '{manifest.id}': distro '{manifest.distro_name}' is not provisioned."
            )

        verify_file = lab_dir / "verify.sh"
        if not verify_file.is_file():
            raise FileNotFoundError(f"Missing verification script: {verify_file}")
        verify_script = verify_file.read_text(encoding="utf-8")

        log(f"Executing verification script on '{manifest.distro_name}'...")
        rc, stdout, stderr = wsl_mgr.execute_script_stdin(
            distro_name=manifest.distro_name,
            script_content=verify_script,
            user="root",
            timeout=120,
        )

        # Parse JSON from stdout
        report_data = None
        # Try to locate JSON object within stdout
        match = re.search(r"(\{[\s\S]*\})", stdout)
        if match:
            try:
                report_data = json.loads(match.group(1))
            except Exception:
                pass

        if not report_data:
            raise ValueError(
                f"verify.sh violated JSON stdout contract.\n"
                f"Exit code: {rc}\n"
                f"Stdout: {stdout}\n"
                f"Stderr: {stderr}"
            )

        report = VerifyReport.model_validate(report_data)
        report.raw_output = stdout

        # Update persisted state
        new_status = LabRuntimeStatus.PASSED if report.passed else LabRuntimeStatus.FAILED
        update_lab_state(
            self.config,
            lab_id=manifest.id,
            distro_name=manifest.distro_name,
            status=new_status,
            last_verified=datetime.now().isoformat(),
            score_passed=report.score_passed,
            score_total=report.score_total,
            checks=report.checks,
        )

        log(f"Verification complete: {'PASSED' if report.passed else 'FAILED'} "
            f"({report.score_passed}/{report.score_total})")
        return report

    def stop_lab(
        self,
        manifest: LabManifest,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Terminate the WSL2 instance for the lab."""
        if progress_callback:
            progress_callback(f"Terminating distro '{manifest.distro_name}'...")

        if wsl_mgr.is_distro_registered(manifest.distro_name):
            wsl_mgr.terminate_distro(manifest.distro_name)

        update_lab_state(
            self.config,
            lab_id=manifest.id,
            distro_name=manifest.distro_name,
            status=LabRuntimeStatus.STOPPED,
        )

    def reset_lab(
        self,
        manifest: LabManifest,
        lab_dir: Path,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Wipe and re-provision the lab from scratch."""
        if progress_callback:
            progress_callback(f"Resetting lab '{manifest.id}'...")

        self.stop_lab(manifest, progress_callback=progress_callback)

        if wsl_mgr.is_distro_registered(manifest.distro_name):
            wsl_mgr.unregister_distro(manifest.distro_name)

        install_dir = self.config.distro_storage_dir / manifest.distro_name
        if install_dir.exists():
            shutil.rmtree(install_dir, ignore_errors=True)

        self.provision_lab(
            manifest=manifest,
            lab_dir=lab_dir,
            force=True,
            progress_callback=progress_callback,
        )
