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

## CompTIA Linux+ (XK0-006) Coverage Matrix

| Domain | Labs | Key Exam Skills |
|---|---|---|
| **1.0 System Management** | **lab-01** (Rocky 9), **lab-09** (Rocky 9), **lab-12** (Ubu 24), **lab-17** (Ubu 24), **lab-19** (Ubu 24) | `fstab`, `.mount` units, `resize2fs`, `logrotate`, `tar`/`rsync`/checksums, `nice`/`ps`, `cron`, `dpkg`/`apt-mark` |
| **2.0 Services & Users** | **lab-02** (Ubu 24), **lab-06** (Ubu 24), **lab-16** (Ubu 24) | `nginx`, `/etc/hosts`, `systemd`, `/etc/skel`, `useradd`/`usermod`/`chage`, `/etc/security/limits.d/` |
| **3.0 Security** | **lab-03** (Rocky 9), **lab-07** (Ubu 24), **lab-11** (Ubu 24), **lab-15** (Ubu 24) | `setgid`, POSIX ACLs, `visudo`, `sshd_config`, `.ssh` modes, CA/CSR/SAN, `chmod`/SUID/sticky bit, `umask` |
| **4.0 Automation & Scripting** | **lab-04** (Ubu 24), **lab-10** (Ubu 24), **lab-13** (Ubu 24), **lab-18** (Ubu 24) | `systemd` timers & `logger`, Git merge/tags/hooks, Ansible playbooks & templates, `grep`/`awk`/`sed`/`find`/Bash |
| **5.0 Troubleshooting** | **lab-05** (Ubu 24), **lab-08** (Ubu 24), **lab-14** (Ubu 24) | `ip netns`/`veth`/routes/`nftables`, cgroup `MemoryMax`/`LimitNOFILE`, `sysctl`, `dnsmasq`/`dig`, socket activation, log analysis |

<details>
<summary>All 19 Labs Quick Reference</summary>

| Lab | Distro | Title | Level |
|---|---|---|---|
| **lab-01** | Rocky Linux 9 | Fix Broken Mount and Service | Intermediate |
| **lab-02** | Ubuntu 24.04 | Fix Nginx, Hosts, and Firewall | Intermediate |
| **lab-03** | Rocky Linux 9 | Shared Directory ACLs and Sudoers | Advanced |
| **lab-04** | Ubuntu 24.04 | Systemd Timer Watchdog Migration | Intermediate |
| **lab-05** | Ubuntu 24.04 | Network Namespace Routing and Firewall | Intermediate |
| **lab-06** | Ubuntu 24.04 | Nginx TLS and Port Conflict | Intermediate |
| **lab-07** | Ubuntu 24.04 | SSH and Password Hardening | Intermediate |
| **lab-08** | Ubuntu 24.04 | Systemd Cgroups and Sysctl Tuning | Advanced |
| **lab-09** | Rocky Linux 9 | Systemd Mount and Filesystem Resize | Advanced |
| **lab-10** | Ubuntu 24.04 | Git Merge, Secrets, and Hooks | Intermediate |
| **lab-11** | Ubuntu 24.04 | Local CA Trust and Nginx TLS | Intermediate |
| **lab-12** | Ubuntu 24.04 | Tar Restore, Rsync, and Checksums | Intermediate |
| **lab-13** | Ubuntu 24.04 | Fix Ansible Playbook and Service | Advanced |
| **lab-14** | Ubuntu 24.04 | DNS, Socket Activation, and Logs | Advanced |
| **lab-15** | Ubuntu 24.04 | File Permissions, Special Bits, and Links | Beginner |
| **lab-16** | Ubuntu 24.04 | Users, Groups, Skel, and Limits | Beginner |
| **lab-17** | Ubuntu 24.04 | Processes, Nice Priority, and Cron | Intermediate |
| **lab-18** | Ubuntu 24.04 | Text Processing, Find, and Scripting | Intermediate |
| **lab-19** | Ubuntu 24.04 | APT Sources, Holds, and DPKG | Intermediate |

</details>

> [!NOTE]
> Upgrading `lplab.exe` automatically refreshes unmodified seed labs in `%LOCALAPPDATA%\linuxplus-labs\labs\` while preserving any user-generated (`lab-20+`) or manually edited labs. If you previously ran v0.4.0, rebuild the Ubuntu base image once with `lplab build-image ubuntu-24.04 --force`.

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
