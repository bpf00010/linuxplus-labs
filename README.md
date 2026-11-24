# lplab: Linux+ WSL Lab Engine

A local hands-on lab engine designed for the **CompTIA Linux+ (XK0-006)** certification. `lplab` provisions isolated WSL2 Linux environments, injects real-world troubleshooting scenarios, verifies solutions with automated validation tests, and generates custom exam-aligned practice scenarios using local or cloud AI models.

> [!CAUTION]
> **CRITICAL PREREQUISITE WARNING:**
> **The program will not launch or provision labs unless Docker Desktop (or Docker Engine / Podman) is running BEFORE `lplab.exe` is opened or run from source.** Docker is required to build and extract the base rootfs container archives (`rockylinux-9.tar` and `ubuntu-24.04.tar`).

---

## Quick Start (Standalone Windows Executable)

No Python installation required.

1. **Prerequisites:**
   - Windows 10 (Build 19041+) or Windows 11 with WSL2 enabled (`wsl --install`).
   - [Windows Terminal](https://aka.ms/terminal) (installed by default on Windows 11).
   - **Docker Desktop** running (must be running before opening `lplab.exe`).
2. **Download:** Download `lplab.exe` from the latest [GitHub Releases](https://github.com/bpf00010/linuxplus-labs/releases).
3. **Run:** Double-click `lplab.exe` or run `lplab` from PowerShell / Command Prompt.
   - By default, running `lplab.exe` with no arguments launches the **Desktop GUI**.
   - On first launch, `lplab.exe` unpacks its dashboard assets and seed labs directly into `%LOCALAPPDATA%\linuxplus-labs\`.
   - Click the base image pills in the dashboard to generate your local `rockylinux-9` and `ubuntu-24.04` rootfs containers.
   - Click **Start Lab** on Lab 01 to boot your first troubleshooting challenge!

---

## Adding `lplab` to Your System PATH

Adding `lplab` to your user `PATH` allows you to launch the GUI, TUI, or CLI directly from any PowerShell or Command Prompt terminal by simply typing `lplab`, `lplab --tui`, or `lplab list`.

### Method A: One-Line PowerShell Command (Recommended)

1. Move or save `lplab.exe` into a permanent directory, e.g. `$HOME\bin`, `C:\tools\lplab`, or `%LOCALAPPDATA%\Programs\lplab`.
2. Open PowerShell and run:

```powershell
# Set the directory where you placed lplab.exe:
$binDir = "$HOME\bin"

# Permanently append to your User PATH:
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$binDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$binDir", "User")
    Write-Host "Added $binDir to PATH. Please restart PowerShell to take effect." -ForegroundColor Green
}
```

### Method B: Windows Settings GUI

1. Press `Win + R`, type `sysdm.cpl` and press **Enter** (or open **Windows Settings** > **System** > **About** > **Advanced system settings**).
2. Click the **Environment Variables...** button.
3. Under **User variables**, select `Path` and click **Edit...**.
4. Click **New** and paste the folder path containing `lplab.exe` (e.g. `C:\Users\<YourUser>\bin`).
5. Click **OK** to save and close the windows.
6. Open a new PowerShell window and run `lplab --help` to confirm!

> [!TIP]
> **For Developers Running from Source:**
> To add the Python virtual environment scripts to your PATH:
> ```powershell
> [Environment]::SetEnvironmentVariable("Path", [Environment]::GetEnvironmentVariable("Path", "User") + ";$((Get-Item .venv\Scripts).FullName)", "User")
> ```

---

## Launch Modes & Usage

### 1. Default: Desktop GUI (Standalone Window)
```powershell
# Simply run lplab (or double-click lplab.exe in File Explorer)
lplab
```
- Launches the native Windows desktop application powered by Microsoft Edge WebView2 and the embedded local FastAPI server on a loopback port.
- Clean monochrome desktop window with zero browser address bar or clutter.
- Automatically hides background console when double-clicked from File Explorer or Start Menu.

### 2. Browser Mode (Any Web Browser)
```powershell
# Open in default web browser (Chrome, Edge, Firefox, Brave)
lplab gui --browser

# Or specify a custom port
lplab gui --browser --port 8765
```

### 3. Interactive Terminal User Interface (TUI)
```powershell
# Launch interactive TUI in your active PowerShell / Windows Terminal
lplab --tui
# or
lplab tui
```
- Full keyboard-navigable split-pane terminal user interface powered by Textual directly inside Windows Terminal or PowerShell.
- High-contrast corporate monochrome theme with live logs, work order briefs, and automated acceptance criteria verification.

### 4. Rich Scriptable CLI Subcommands
```powershell
# List available labs and status table
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

### 5. Desktop & Start Menu Shortcuts
Run the included shortcut helper script:
```powershell
powershell -ExecutionPolicy Bypass -File .\create_shortcut.ps1
```
- Automatically creates clean shortcuts on your **Desktop** (`lplab.lnk`) and in your **Start Menu** (`Linux+ Lab Engine.lnk`).

---

## Core Architecture & Safety Guarantees

- **Dual-Mode Interface:**
  - **Desktop GUI:** Native Windows desktop window powered by Microsoft Edge WebView2 (`pywebview` + local FastAPI server on a loopback port).
  - **Terminal TUI:** Interactive split-pane terminal user interface powered by Textual.
  - **Scriptable CLI:** Rich-formatted command line interface built with Typer.
- **Strict Namespace Guard:** Every managed WSL distribution is prefixed with `lplab-` (e.g. `lplab-lab-01-systemd-storage`). Destructive operations (`terminate`, `unregister`) enforce this safeguard to ensure personal distributions (e.g. `Ubuntu`, `Debian`) are never affected.
- **Full systemd Environment:** Booted with native WSL2 systemd configuration (`systemd=true`), verified via `ps -p 1 -o comm=` and `systemctl is-system-running`.
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
- **Docker Desktop** running.
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
