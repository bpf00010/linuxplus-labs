# lplab: Linux+ WSL Lab Engine

A local hands-on lab engine designed for the **CompTIA Linux+ (XK0-006)** certification. `lplab` provisions isolated WSL2 Linux environments, injects real-world troubleshooting scenarios, verifies solutions with automated validation tests, and generates custom exam-aligned practice scenarios using local or cloud AI models.

---

## Quick Start (Standalone Windows Executable)

No Python installation required.

1. **Download:** Download `lplab.exe` from the latest [GitHub Releases](https://github.com/bpf00010/linuxplus-labs/releases).
2. **Prerequisites:**
   - Windows 10 (Build 19041+) or Windows 11 with WSL2 enabled (`wsl --install`).
   - [Windows Terminal](https://aka.ms/terminal) (installed by default on Windows 11).
   - Docker Desktop or Podman running once to build base image rootfs archives.
3. **Run:** Double-click `lplab.exe`.
   - On first launch, `lplab.exe` unpacks its dashboard assets and seed labs directly into `%LOCALAPPDATA%\linuxplus-labs\`.
   - Click the base image pills in the dashboard to generate your local `rockylinux-9` and `ubuntu-24.04` rootfs containers.
   - Click **Start Lab** on Lab 01 to boot your first troubleshooting challenge!

---

## Core Architecture & Safety Guarantees

- **Dual-Mode Interface:**
  - **Desktop GUI:** Native Windows desktop window powered by Microsoft Edge WebView2 (`pywebview` + local FastAPI server on a loopback port).
  - **Terminal TUI:** Interactive split-pane terminal user interface powered by Textual.
  - **Scriptable CLI:** Rich-formatted command line interface built with Typer.
- **Strict Namespace Guard:** Every managed WSL distribution is prefixed with `lplab-` (e.g. `lplab-lab-01-systemd-storage`). Destructive operations (`terminate`, `unregister`) enforce this safeguard to ensure personal distributions (e.g. `Ubuntu`, `Debian`) are never affected.
- **Full systemd Environment:** Booted with native WSL2 systemd configuration (`systemd=true`), verified via `systemctl is-system-running`.
- **Pure Stdin Script Execution:** All setup and verification scripts stream over stdin (`bash -s`), avoiding file locking or mount issues.
- **Isolated Network Namespaces:** Network and firewall challenges use dedicated network namespaces (`ip netns`) or isolated nftables tables (`table inet lplab_<id>`), ensuring host networking remains completely untouched.

---

## Included Hands-On Labs (XK0-006)

| Lab ID | Distro | Objective Focus | Scenario Highlights |
|---|---|---|---|
| **lab-01** | Rocky Linux 9 | System Management, Troubleshooting | Corrupted `/etc/fstab` loop mount, masked service, logrotate limits |
| **lab-02** | Ubuntu 24.04 | Networking, Firewall, Services | Broken Nginx config, incorrect `/etc/hosts`, scoped nftables drop rule |
| **lab-03** | Rocky Linux 9 | Security, Access Controls | Shared directory permissions (`setgid`, POSIX ACLs), least-privilege sudo |
| **lab-04** | Ubuntu 24.04 | Automation, Scripting, Systemd | Migrate broken legacy cron to `systemd` oneshot service & active timer |
| **lab-05** | Ubuntu 24.04 | Troubleshooting, Systemd, Security | Multi-namespace `veth` routing, default gateway, and scoped `nftables` |
| **lab-06** | Ubuntu 24.04 | Services, Security, Troubleshooting | Identify port conflict, harden TLS keys (`0600`), and fix Nginx upstream |
| **lab-07** | Ubuntu 24.04 | Security, Services and Users | Harden OpenSSH daemon, `AllowGroups sshusers`, `.ssh` permissions, `chage` |
| **lab-08** | Ubuntu 24.04 | Troubleshooting, System Management | Fix cgroup `MemoryMax` & `LimitNOFILE` drop-ins, mask runaway logger, `sysctl` |
| **lab-09** | Rocky Linux 9 | System Management, Troubleshooting | Expand loop disk image, `resize2fs`, and harden systemd `.mount` unit |

> [!TIP]
> **Upgrading Base Images:** If you previously generated base `.tar` images, run `lplab build-image all --force` to bake in the latest `systemd`, `dbus-user-session`, and `policy-rc.d` fixes.

---

## CLI & TUI Usage

### Launch Interactive TUI
```powershell
lplab ui
# or simply
lplab
```

### CLI Subcommands
```powershell
# List available labs and status
lplab list

# Start a specific lab (launches Windows Terminal tab)
lplab start lab-01

# Verify student fixes (emits structured test report)
lplab verify lab-01

# Stop a running lab
lplab stop lab-01

# Reset and restore lab to initial broken state
lplab reset lab-01 --yes

# Build base image rootfs archives
lplab build-image all
```

---

## AI Lab Generator Setup

`lplab` includes an automated scenario generator that drafts fresh CompTIA Linux+ challenges, complete with a zero-spoiler briefing, provisioning script, and JSON test validator.

To configure your LLM provider, copy `config.example.yaml` to `%LOCALAPPDATA%\linuxplus-labs\config.yaml` (or `./config.yaml` in source mode):

### Local Ollama (Default)
```yaml
ai:
  base_url: "http://localhost:11434/v1"
  api_key: "ollama"
  model: "llama3"
```

### OpenRouter / OpenAI
```yaml
ai:
  base_url: "https://openrouter.ai/api/v1"
  api_key: "sk-or-v1-..."
  model: "anthropic/claude-3.5-sonnet"
```

Generate a scenario via CLI:
```powershell
lplab generate --domain security --topic "SSH Key Hardening and Chage Expiry" --base-image rockylinux-9
```

---

## Development Setup (From Source)

### 1. Requirements
- Windows 10/11 with WSL2 enabled.
- Python 3.11, 3.12, or 3.13.
- `uv` (recommended) or standard `pip`.

### 2. Install Editable Package
```powershell
git clone https://github.com/bpf00010/linuxplus-labs.git
cd linuxplus-labs
uv venv --python 3.12 .venv
.venv\Scripts\activate
pip install -e ".[dev,build]"
```

### 3. Run Tests
```powershell
pytest -v
```

### 4. Build Standalone Executable
```powershell
python scripts/build_exe.py
```
This produces `dist/lplab.exe` with bundled icons, seed scenarios, and web assets.

---

## License

This project is licensed under the [MIT License](LICENSE).
