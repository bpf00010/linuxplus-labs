"""Root filesystem tarball builder using Docker or Podman."""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, Optional, Tuple

UBUNTU_PACKAGES = [
    "systemd",
    "systemd-sysv",
    "sudo",
    "iproute2",
    "nftables",
    "openssh-server",
    "acl",
    "logrotate",
    "curl",
    "jq",
    "e2fsprogs",
    "util-linux",
    "nginx",
    "passwd",
    "procps",
]

ROCKY_PACKAGES = [
    "systemd",
    "sudo",
    "iproute",
    "nftables",
    "openssh-server",
    "acl",
    "logrotate",
    "curl",
    "jq",
    "e2fsprogs",
    "util-linux",
    "podman",
    "passwd",
    "which",
    "findutils",
    "procps-ng",
]


def detect_container_runtime() -> Tuple[Optional[str], bool]:
    """Detect available container runtime (podman or docker).

    Returns:
        (runtime_cmd, is_wsl_bridged)
        E.g. ("docker", False) or ("podman", False) or ("docker", True)
    """
    # 1. Native check
    for cmd in ["podman", "docker"]:
        if shutil.which(cmd):
            # Check if engine responds
            try:
                res = subprocess.run([cmd, "info"], capture_output=True, timeout=5)
                if res.returncode == 0:
                    return cmd, False
            except Exception:
                pass

    # 2. WSL bridge check if on Windows
    if sys.platform == "win32":
        for cmd in ["podman", "docker"]:
            try:
                res = subprocess.run(
                    ["wsl.exe", "--", cmd, "info"],
                    capture_output=True,
                    timeout=5,
                )
                if res.returncode == 0:
                    return cmd, True
            except Exception:
                pass

    # Check if binaries exist without info check (e.g. docker cli present even if daemon stopped)
    for cmd in ["podman", "docker"]:
        if shutil.which(cmd):
            return cmd, False

    return None, False


def generate_dockerfile(base_image: str) -> str:
    """Generate Dockerfile for building the lab base image."""
    if base_image == "ubuntu-24.04":
        pkgs = " ".join(UBUNTU_PACKAGES)
        return f"""FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends {pkgs} \\
    && apt-get clean && rm -rf /var/lib/apt/lists/*
CMD ["/sbin/init"]
"""
    elif base_image == "rockylinux-9":
        pkgs = " ".join(ROCKY_PACKAGES)
        return f"""FROM rockylinux:9
RUN dnf install -y epel-release || true
RUN dnf install -y --allowerasing {pkgs} \\
    && dnf clean all
CMD ["/sbin/init"]
"""
    else:
        raise ValueError(f"Unsupported base image: {base_image}")


def build_rootfs_tar(
    base_image: str,
    output_dir: Path,
    force: bool = False,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> Path:
    """Build rootfs tarball using Podman or Docker and cache it in base-images/.

    Target tar names: `rockylinux-9.tar` or `ubuntu-24.04.tar`.
    """
    def log(msg: str) -> None:
        if progress_callback:
            progress_callback(msg)

    output_dir.mkdir(parents=True, exist_ok=True)
    tar_path = output_dir / f"{base_image}.tar"

    if tar_path.is_file() and not force:
        log(f"Cached image archive found: {tar_path.name} (skipping build). Use --force to rebuild.")
        return tar_path

    runtime, is_wsl = detect_container_runtime()
    if not runtime:
        raise RuntimeError(
            "Neither Podman nor Docker was found or responding. "
            "Please ensure Docker Desktop / Podman is running or provide prebuilt "
            f"archives at {tar_path}."
        )

    log(f"Building base image '{base_image}' using {runtime} (WSL bridged: {is_wsl})...")
    tag = f"lplab-base-{base_image}:latest"
    container_name = f"lplab-export-{base_image}"

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        df_path = tmp_path / "Dockerfile"
        df_content = generate_dockerfile(base_image)
        df_path.write_text(df_content, encoding="utf-8")

        build_cmd_prefix = ["wsl.exe", "--", runtime] if is_wsl else [runtime]

        # 1. Build image
        log(f"Step 1/3: Building container image {tag}...")
        b_res = subprocess.run(
            [*build_cmd_prefix, "build", "-t", tag, str(tmp_path)],
            capture_output=True,
            text=True,
        )
        if b_res.returncode != 0:
            raise RuntimeError(f"Failed to build container image: {b_res.stderr or b_res.stdout}")

        # 2. Create container
        log(f"Step 2/3: Creating temporary container {container_name}...")
        # Clean existing if any
        subprocess.run(
            [*build_cmd_prefix, "rm", "-f", container_name],
            capture_output=True,
        )
        c_res = subprocess.run(
            [*build_cmd_prefix, "create", "--name", container_name, tag],
            capture_output=True,
            text=True,
        )
        if c_res.returncode != 0:
            raise RuntimeError(f"Failed to create container: {c_res.stderr or c_res.stdout}")

        # 3. Export to tar
        log(f"Step 3/3: Exporting container rootfs to {tar_path.name}...")
        try:
            if not is_wsl:
                # Direct export
                exp_res = subprocess.run(
                    [runtime, "export", container_name, "-o", str(tar_path)],
                    capture_output=True,
                    text=True,
                )
                if exp_res.returncode != 0:
                    raise RuntimeError(f"Failed to export container: {exp_res.stderr}")
            else:
                # Export via stream from WSL
                with open(tar_path, "wb") as f_out:
                    exp_proc = subprocess.Popen(
                        ["wsl.exe", "--", runtime, "export", container_name],
                        stdout=f_out,
                        stderr=subprocess.PIPE,
                    )
                    _, exp_err = exp_proc.communicate()
                    if exp_proc.returncode != 0:
                        raise RuntimeError(f"Failed to export container via WSL: {exp_err}")
        finally:
            # Clean up container
            subprocess.run(
                [*build_cmd_prefix, "rm", "-f", container_name],
                capture_output=True,
            )

    log(f"Successfully created base image archive: {tar_path}")
    return tar_path
