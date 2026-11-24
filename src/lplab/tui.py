"""Textual TUI for browsing, provisioning, launching, and verifying Linux+ labs."""

from pathlib import Path
import time
from typing import Dict, List, Optional, Tuple
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Markdown,
    RichLog,
    Select,
    Static,
    TabbedContent,
    TabPane,
)

from lplab.ai_generator import AILabGenerator
from lplab.config import AppConfig, load_config
from lplab.lab_engine import LabEngine
from lplab.models import LabManifest, LabRuntimeStatus, LabStateRecord, VerifyReport


class ResetConfirmModal(ModalScreen[bool]):
    """Corporate confirmation modal before wiping and resetting a lab."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    ResetConfirmModal {
        align: center middle;
        background: rgba(15, 20, 25, 0.85);
    }
    #confirm-dialog {
        padding: 1 2;
        width: 64;
        height: auto;
        border: solid #2a3441;
        background: #161c24;
        color: #e6edf3;
    }
    #confirm-buttons {
        margin-top: 1;
        align: right middle;
    }
    Button {
        margin-left: 2;
        background: #1d2530;
        color: #e6edf3;
        border: solid #2a3441;
    }
    Button:hover {
        background: #2a3441;
        border: solid #3e4c5e;
    }
    #btn-reset {
        background: #da3633;
        color: #ffffff;
        text-style: bold;
        border: solid #f85149;
    }
    #btn-reset:hover {
        background: #f85149;
    }
    """

    def __init__(self, lab_title: str):
        super().__init__()
        self.lab_title = lab_title

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("[bold #f85149]CONFIRM LAB RESET[/bold #f85149]\n"),
            Label(f"Are you sure you want to completely wipe and rebuild:\n[bold #e6edf3]{self.lab_title}[/bold #e6edf3]?\n"),
            Label("[#6e7b8b]All modifications, runtime state, and files will be permanently erased.[/#6e7b8b]"),
            Horizontal(
                Button("Cancel", variant="default", id="btn-cancel"),
                Button("Reset Lab", variant="default", id="btn-reset"),
                id="confirm-buttons",
            ),
            id="confirm-dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-reset":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_cancel(self) -> None:
        """Dismiss modal cleanly on Escape."""
        self.dismiss(False)


class GenerateModal(ModalScreen[Optional[Tuple[str, str, str]]]):
    """Corporate modal dialog for generating a new AI lab scenario."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    GenerateModal {
        align: center middle;
        background: rgba(15, 20, 25, 0.85);
    }
    #gen-dialog {
        padding: 1 2;
        width: 72;
        height: auto;
        border: solid #2a3441;
        background: #161c24;
        color: #e6edf3;
    }
    .form-item {
        margin-bottom: 1;
    }
    Input {
        background: #0f1419;
        color: #e6edf3;
        border: solid #2a3441;
    }
    Input:focus {
        border: solid #2f6feb;
    }
    Select {
        background: #0f1419;
        color: #e6edf3;
        border: solid #2a3441;
    }
    Select:focus {
        border: solid #2f6feb;
    }
    #gen-buttons {
        margin-top: 1;
        align: right middle;
    }
    Button {
        margin-left: 2;
        background: #1d2530;
        color: #e6edf3;
        border: solid #2a3441;
    }
    Button:hover {
        background: #2a3441;
        border: solid #3e4c5e;
    }
    #btn-generate {
        background: #2f6feb;
        color: #ffffff;
        text-style: bold;
        border: solid #3d7bf5;
    }
    #btn-generate:hover {
        background: #3d7bf5;
    }
    """

    DOMAINS = [
        ("System Management", "system_management"),
        ("Services and Users", "services_and_users"),
        ("Security", "security"),
        ("Automation & Scripting", "automation_scripting"),
        ("Troubleshooting", "troubleshooting"),
    ]

    IMAGES = [
        ("Rocky Linux 9 (RHEL-compatible)", "rockylinux-9"),
        ("Ubuntu 24.04 LTS (Debian-compatible)", "ubuntu-24.04"),
    ]

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("[bold white]GENERATE COMPTIA LINUX+ AI LAB[/bold white]\n"),
            Label("[dim]Domain:[/dim]"),
            Select(self.DOMAINS, value="system_management", id="select-domain", classes="form-item"),
            Label("[dim]Topic / Scenario Concept:[/dim]"),
            Input(placeholder="e.g. LVM snapshot volume recovery or SSH hardening", id="input-topic", classes="form-item"),
            Label("[dim]Base Distro:[/dim]"),
            Select(self.IMAGES, value="rockylinux-9", id="select-image", classes="form-item"),
            Horizontal(
                Button("Cancel", variant="default", id="btn-cancel"),
                Button("Generate Lab", variant="default", id="btn-generate"),
                id="gen-buttons",
            ),
            id="gen-dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-generate":
            domain = self.query_one("#select-domain", Select).value
            topic = self.query_one("#input-topic", Input).value.strip()
            image = self.query_one("#select-image", Select).value
            if not topic:
                topic = "General troubleshooting scenario"
            self.dismiss((str(domain), topic, str(image)))
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        """Dismiss modal cleanly on Escape."""
        self.dismiss(None)


class LabEngineApp(App):
    """Textual split-pane launcher UI for Linux+ WSL Lab Engine with corporate monochrome styling."""

    TITLE = "LPLAB  |  LINUX+ WSL LAB ENGINE"
    SUB_TITLE = "CompTIA Linux+ (XK0-006) Hands-On Practice"

    # Single-key bindings do NOT use priority=True so inputs in modals are never intercepted
    BINDINGS = [
        Binding("enter", "start_selected", "Launch Lab", priority=False),
        Binding("v", "verify_selected", "Verify", priority=False),
        Binding("r", "reset_selected", "Reset", priority=False),
        Binding("s", "stop_selected", "Stop", priority=False),
        Binding("g", "open_generate", "Generate Lab", priority=False),
        Binding("q", "quit", "Quit", priority=False),
    ]

    CSS = """
    Screen {
        layout: vertical;
        background: #0f1419;
        color: #e6edf3;
    }
    Header {
        background: #161c24;
        color: #e6edf3;
        dock: top;
        height: 1;
    }
    Footer {
        background: #161c24;
        color: #9ba7b4;
        dock: bottom;
        height: 1;
    }
    #main-container {
        layout: horizontal;
        height: 1fr;
        background: #0f1419;
    }
    #left-pane {
        width: 36%;
        height: 100%;
        border-right: solid #2a3441;
        background: #0f1419;
    }
    #right-pane {
        width: 64%;
        height: 100%;
        layout: vertical;
        background: #0f1419;
    }
    #lab-header-banner {
        height: auto;
        padding: 1 2;
        background: #161c24;
        border-bottom: solid #2a3441;
        color: #e6edf3;
    }
    #action-bar {
        height: auto;
        padding: 0 1;
        margin-top: 1;
        margin-bottom: 0;
    }
    #action-bar Button {
        margin-right: 1;
        background: #1d2530;
        color: #e6edf3;
        border: solid #2a3441;
        min-width: 14;
    }
    #action-bar Button:hover {
        background: #2a3441;
        border: solid #3e4c5e;
        color: #ffffff;
    }
    #btn-action-start {
        background: #2f6feb;
        color: #ffffff;
        text-style: bold;
        border: solid #3d7bf5;
    }
    #btn-action-start:hover {
        background: #3d7bf5;
        color: #ffffff;
    }
    #job-status-strip {
        padding: 0 2;
        margin-top: 1;
        margin-bottom: 1;
        color: #9ba7b4;
        text-style: bold;
        height: 1;
        background: #161c24;
        border-bottom: solid #2a3441;
    }
    DataTable {
        height: 100%;
        background: #0f1419;
        color: #e6edf3;
        border: none;
    }
    DataTable > .datatable--cursor {
        background: #2f6feb;
        color: #ffffff;
        text-style: bold;
    }
    DataTable > .datatable--header {
        background: #161c24;
        color: #e6edf3;
        text-style: bold;
    }
    #tabbed-content {
        height: 1fr;
        background: #0f1419;
    }
    TabbedContent ContentSwitcher {
        background: #0f1419;
    }
    TabPane {
        background: #0f1419;
        padding: 0;
    }
    Tabs {
        background: #161c24;
        color: #9ba7b4;
    }
    Tab.-active {
        color: #ffffff;
        text-style: bold;
        background: #1d2530;
        border-bottom: tall #2f6feb;
    }
    #brief-scroll {
        height: 100%;
        padding: 1 2;
        background: #0f1419;
    }
    #lab-meta-box {
        height: auto;
        margin-bottom: 1;
        padding: 1;
        border: solid #2a3441;
        background: #161c24;
        color: #e6edf3;
    }
    #acceptance-criteria-box {
        height: auto;
        margin-bottom: 1;
        padding: 1;
        border: solid #2a3441;
        background: #161c24;
        color: #e6edf3;
    }
    #work-order-markdown {
        height: auto;
        color: #e6edf3;
        background: #0f1419;
    }
    #verify-scroll {
        height: 100%;
        padding: 1 2;
        background: #0f1419;
    }
    #verify-content {
        height: auto;
        color: #e6edf3;
        background: #0f1419;
    }
    RichLog {
        height: 100%;
        border: none;
        background: #0f1419;
        color: #e6edf3;
        padding: 1 2;
    }
    """

    def __init__(self, config: Optional[AppConfig] = None):
        super().__init__()
        self.config = config or load_config()
        self.engine = LabEngine(self.config)
        self.labs: List[Tuple[LabManifest, Path]] = []
        self.selected_manifest: Optional[LabManifest] = None
        self.selected_path: Optional[Path] = None
        self._last_start_time: float = 0.0
        self.log_history: List[str] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="main-container"):
            with Vertical(id="left-pane"):
                yield DataTable(id="labs-table", cursor_type="row")
            with Vertical(id="right-pane"):
                yield Static(id="lab-header-banner")
                with Horizontal(id="action-bar"):
                    yield Button("Launch [Enter]", variant="default", id="btn-action-start")
                    yield Button("Verify [v]", variant="default", id="btn-action-verify")
                    yield Button("Stop [s]", variant="default", id="btn-action-stop")
                    yield Button("Reset [r]", variant="default", id="btn-action-reset")
                    yield Button("New Lab [g]", variant="default", id="btn-action-generate")
                yield Static("STATUS: IDLE", id="job-status-strip")
                with TabbedContent(initial="tab-brief", id="tabbed-content"):
                    with TabPane("Work Order", id="tab-brief"):
                        with VerticalScroll(id="brief-scroll"):
                            yield Static(id="lab-meta-box")
                            yield Static(id="acceptance-criteria-box")
                            yield Markdown(id="work-order-markdown")
                    with TabPane("Acceptance Criteria & Verification", id="tab-verify"):
                        with VerticalScroll(id="verify-scroll"):
                            yield Static(id="verify-content")
                    with TabPane("Live Logs", id="tab-logs"):
                        yield RichLog(id="log-view", auto_scroll=True, wrap=True, markup=False)
        yield Footer()

    async def on_mount(self) -> None:
        table = self.query_one("#labs-table", DataTable)
        table.add_columns("ID", "Title", "Base", "Status")
        await self.refresh_labs()

    def set_job_status(self, status: str) -> None:
        """Update visible status strip."""
        try:
            strip = self.query_one("#job-status-strip", Static)
            strip.update(f"STATUS: {status.upper()}")
        except Exception:
            pass

    def log_message(self, message: str) -> None:
        """Post a line to persistent buffer and live RichLog."""
        self.log_history.append(message)
        try:
            log_view = self.query_one("#log-view", RichLog)
            log_view.write(message)
        except Exception:
            pass

    def _switch_to_tab(self, tab_id: str) -> None:
        """Helper to switch active tab in right pane."""
        tabbed = self.query_one("#tabbed-content", TabbedContent)
        tabbed.active = tab_id
        if tab_id == "tab-logs":
            try:
                log_view = self.query_one("#log-view", RichLog)
                if len(log_view.lines) < len(self.log_history):
                    log_view.clear()
                    for line in self.log_history:
                        log_view.write(line)
            except Exception:
                pass

    def format_badge(self, status: LabRuntimeStatus, record: Optional[LabStateRecord], rich: bool = False) -> str:
        """Format uniform corporate badge for table view and banner."""
        if status == LabRuntimeStatus.NOT_PROVISIONED:
            return "[#9ba7b4][NEW][/#9ba7b4]" if rich else "[NEW]"
        elif status == LabRuntimeStatus.RUNNING:
            return "[bold #2ea043][RUNNING][/bold #2ea043]" if rich else "[RUNNING]"
        elif status == LabRuntimeStatus.STOPPED:
            return "[#9ba7b4][STOPPED][/#9ba7b4]" if rich else "[STOPPED]"
        elif status == LabRuntimeStatus.PASSED:
            p = record.score_passed if record else 0
            t = record.score_total if record else 0
            return f"[bold #2ea043][PASS {p}/{t}][/bold #2ea043]" if rich else f"[PASS {p}/{t}]"
        elif status == LabRuntimeStatus.FAILED:
            p = record.score_passed if record else 0
            t = record.score_total if record else 0
            return f"[bold #f85149][FAIL {p}/{t}][/bold #f85149]" if rich else f"[FAIL {p}/{t}]"
        return f"[{status.value.upper()}]"

    async def refresh_labs(self) -> None:
        """Reload labs from disk and populate table, preserving current selection."""
        current_id = self.selected_manifest.id if self.selected_manifest else None
        self.labs = self.engine.discover_labs()
        table = self.query_one("#labs-table", DataTable)
        table.clear()

        target_row = 0
        for idx, (manifest, path) in enumerate(self.labs):
            status, record = self.engine.get_lab_status(manifest)
            badge = self.format_badge(status, record)
            base_short = "Rocky9" if "rocky" in manifest.base_image else "Ubu24"
            table.add_row(
                manifest.id,
                manifest.title,
                base_short,
                badge,
                key=manifest.id,
            )
            if current_id and manifest.id == current_id:
                target_row = idx

        if self.labs:
            self.selected_manifest, self.selected_path = self.labs[target_row]
            if table.row_count > 0:
                table.move_cursor(row=target_row)
            await self.update_details_view()

    def action_refresh(self) -> None:
        """Trigger async refresh from a worker thread."""
        self.run_worker(self.refresh_labs())

    async def select_lab_by_id(self, lab_id: str) -> None:
        """Select a lab by ID and update views asynchronously."""
        for m, p in self.labs:
            if m.id == lab_id:
                self.selected_manifest = m
                self.selected_path = p
                await self.update_details_view()
                break

    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle Enter key or double-click on a table row to select and launch."""
        row_key = event.row_key.value
        await self.select_lab_by_id(row_key)
        self.action_start_selected()

    async def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Handle keyboard arrow navigation or single click."""
        if event.row_key:
            row_key = event.row_key.value
            await self.select_lab_by_id(row_key)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Route Action Bar button clicks to action handlers."""
        btn_id = event.button.id
        if btn_id == "btn-action-start":
            self.action_start_selected()
        elif btn_id == "btn-action-verify":
            self.action_verify_selected()
        elif btn_id == "btn-action-stop":
            self.action_stop_selected()
        elif btn_id == "btn-action-reset":
            self.action_reset_selected()
        elif btn_id == "btn-action-generate":
            self.action_open_generate()

    def update_header_banner(self) -> None:
        """Update top metadata banner of selected lab."""
        banner = self.query_one("#lab-header-banner", Static)
        if not self.selected_manifest:
            banner.update("[#6e7b8b]NO LAB SELECTED[/#6e7b8b]")
            return
        m = self.selected_manifest
        status, record = self.engine.get_lab_status(m)
        badge = self.format_badge(status, record, rich=True)
        banner.update(
            f"[bold #e6edf3]{m.id.upper()}[/bold #e6edf3]  |  [bold #e6edf3]{m.title}[/bold #e6edf3]  |  {badge}\n"
            f"[#9ba7b4]DISTRO:[/#9ba7b4] [#e6edf3]{m.distro_name}[/#e6edf3]  |  [#9ba7b4]BASE:[/#9ba7b4] [#e6edf3]{m.base_image}[/#e6edf3]  |  "
            f"[#9ba7b4]DIFFICULTY:[/#9ba7b4] [#e6edf3]{m.difficulty.upper()}[/#e6edf3]  |  [#9ba7b4]EST. TIME:[/#9ba7b4] [#e6edf3]{m.estimated_minutes}m[/#e6edf3]"
        )

    async def update_details_view(self) -> None:
        """Update right-pane Banner, Work Order, and Objectives/Verification tabs."""
        if not self.selected_manifest or not self.selected_path:
            return

        m = self.selected_manifest
        p = self.selected_path
        status, record = self.engine.get_lab_status(m)

        # 1. Update Header Banner
        self.update_header_banner()

        # 2. Update Lab Meta Box in Work Order Tab
        try:
            meta_box = self.query_one("#lab-meta-box", Static)
            domains_str = ", ".join(m.xk0_006_domains) if m.xk0_006_domains else "General"
            meta_box.update(
                f"[bold #2f6feb]LAB METADATA[/bold #2f6feb]\n"
                f"[bold #e6edf3]{m.id.upper()}: {m.title}[/bold #e6edf3]\n"
                f"[#9ba7b4]Target Distro:[/#9ba7b4] [#e6edf3]{m.distro_name}[/#e6edf3]  |  "
                f"[#9ba7b4]Base Image:[/#9ba7b4] [#e6edf3]{m.base_image}[/#e6edf3]  |  "
                f"[#9ba7b4]Difficulty:[/#9ba7b4] [#e6edf3]{m.difficulty.upper()}[/#e6edf3]  |  "
                f"[#9ba7b4]Domains:[/#9ba7b4] [#e6edf3]{domains_str}[/#e6edf3]  |  "
                f"[#9ba7b4]Est. Time:[/#9ba7b4] [#e6edf3]{m.estimated_minutes}m[/#e6edf3]"
            )
        except Exception:
            pass

        # 3. Update Acceptance Criteria Box in Work Order Tab
        try:
            crit_box = self.query_one("#acceptance-criteria-box", Static)
            lines = ["[bold #2f6feb]ACCEPTANCE CRITERIA & REQUIREMENTS (XK0-006):[/bold #2f6feb]"]
            if m.objectives:
                for idx, obj in enumerate(m.objectives, 1):
                    lines.append(f"  [bold #2f6feb][{idx}][/bold #2f6feb] [#e6edf3]{obj}[/#e6edf3]")
            else:
                lines.append("  [#6e7b8b]No explicit objectives listed in manifest.[/#6e7b8b]")
            crit_box.update("\n".join(lines))
        except Exception:
            pass

        # 4. Update Work Order Markdown
        try:
            brief_file = p / "BRIEF.md"
            content = brief_file.read_text(encoding="utf-8") if brief_file.is_file() else "# No Brief Found"
            markdown_widget = self.query_one("#work-order-markdown", Markdown)
            await markdown_widget.update(content)
        except Exception:
            pass

        # 5. Update Acceptance Criteria & Verification Tab
        try:
            verify_widget = self.query_one("#verify-content", Static)
            sections = []
            sections.append("[bold #2f6feb]ACCEPTANCE CRITERIA / OBJECTIVES (XK0-006):[/bold #2f6feb]\n")
            if m.objectives:
                for idx, obj in enumerate(m.objectives, 1):
                    sections.append(f"  [{idx}] {obj}")
            else:
                sections.append("  [#6e7b8b]No explicit objectives listed in manifest.[/#6e7b8b]")
            sections.append("")

            sections.append("[bold #2f6feb]VERIFICATION STATUS & CHECK BREAKDOWN:[/bold #2f6feb]\n")
            if record and record.last_verified:
                badge = self.format_badge(record.status, record, rich=True)
                sections.append(f"  Status: {badge}")
                sections.append(f"  Score:  [bold #e6edf3]{record.score_passed} / {record.score_total}[/bold #e6edf3]")
                sections.append(f"  Tested: [#9ba7b4]{record.last_verified}[/#9ba7b4]\n")
                if record.checks:
                    for chk in record.checks:
                        sym = "[bold #2ea043][PASS][/bold #2ea043]" if chk.passed else "[bold #f85149][FAIL][/bold #f85149]"
                        sections.append(f"  {sym} [{chk.id}]: {chk.description}")
                        if chk.details:
                            sections.append(f"         [#6e7b8b]{chk.details}[/#6e7b8b]")
                    sections.append("")
                sections.append("[#9ba7b4]Press 'v' or click Verify [v] to re-run automated checks.[/#9ba7b4]")
            else:
                sections.append(
                    f"  No verification run recorded yet for {m.id}.\n\n"
                    "  Press 'v' or click Verify [v] to execute non-destructive automated checks."
                )

            verify_widget.update("\n".join(sections))
        except Exception:
            pass

    @work(thread=True)
    def action_start_selected(self) -> None:
        """Launch or provision selected lab in background thread."""
        now = time.time()
        # Debounce double-trigger from Enter keybinding + DataTable row selection
        if now - self._last_start_time < 0.8:
            return
        self._last_start_time = now

        if not self.selected_manifest or not self.selected_path:
            return
        m = self.selected_manifest
        p = self.selected_path
        self.call_from_thread(self.set_job_status, f"PROVISIONING {m.id}...")
        self.call_from_thread(self._switch_to_tab, "tab-logs")
        self.call_from_thread(self.log_message, f"[{m.id}] Starting lab launch: {m.title}...")
        try:
            self.engine.start_lab(
                manifest=m,
                lab_dir=p,
                progress_callback=lambda msg: self.call_from_thread(self.log_message, f"  {msg}"),
            )
            self.call_from_thread(self.log_message, f"[{m.id}] Lab terminal launched successfully.")
        except Exception as e:
            self.call_from_thread(self.log_message, f"[{m.id}] [ERR] Failed to start lab: {e}")
        finally:
            self.call_from_thread(self.set_job_status, "IDLE")
        self.call_from_thread(self.action_refresh)

    @work(thread=True)
    def action_verify_selected(self) -> None:
        """Execute verify.sh on selected lab in background thread."""
        if not self.selected_manifest or not self.selected_path:
            return
        m = self.selected_manifest
        p = self.selected_path
        self.call_from_thread(self.set_job_status, f"VERIFYING {m.id}...")
        self.call_from_thread(self.log_message, f"[{m.id}] Running verification checks...")
        try:
            report: VerifyReport = self.engine.verify_lab(
                manifest=m,
                lab_dir=p,
                progress_callback=lambda msg: self.call_from_thread(self.log_message, f"  {msg}"),
            )
            res_str = "PASSED" if report.passed else "FAILED"
            msg = f"[{m.id}] Verification {res_str}: {report.score_passed}/{report.score_total}"
            self.call_from_thread(self.log_message, msg)
            for chk in report.checks:
                chk_sym = "[PASS]" if chk.passed else "[FAIL]"
                self.call_from_thread(
                    self.log_message,
                    f"  {chk_sym} [{chk.id}] {chk.description}: {chk.details}"
                )

            # Update verification widget & switch tab to verification
            def update_ui() -> None:
                self.run_worker(self.update_details_view())
                self._switch_to_tab("tab-verify")

            self.call_from_thread(update_ui)
        except Exception as e:
            self.call_from_thread(self.log_message, f"[{m.id}] [ERR] Verification failed: {e}")
        finally:
            self.call_from_thread(self.set_job_status, "IDLE")

        self.call_from_thread(self.action_refresh)

    def action_reset_selected(self) -> None:
        """Prompt confirmation modal before resetting."""
        if not self.selected_manifest or not self.selected_path:
            return

        def handle_reset(confirm: Optional[bool]) -> None:
            if confirm:
                self._run_reset_worker()

        self.push_screen(ResetConfirmModal(self.selected_manifest.title), handle_reset)

    @work(thread=True)
    def _run_reset_worker(self) -> None:
        """Background reset worker."""
        if not self.selected_manifest or not self.selected_path:
            return
        m = self.selected_manifest
        p = self.selected_path
        self.call_from_thread(self.set_job_status, f"RESETTING {m.id}...")
        self.call_from_thread(self._switch_to_tab, "tab-logs")
        self.call_from_thread(self.log_message, f"[{m.id}] Resetting and wiping distro '{m.distro_name}'...")
        try:
            self.engine.reset_lab(
                manifest=m,
                lab_dir=p,
                progress_callback=lambda msg: self.call_from_thread(self.log_message, f"  {msg}"),
            )
            self.call_from_thread(self.log_message, f"[{m.id}] Reset complete. Lab rebuilt cleanly.")
        except Exception as e:
            self.call_from_thread(self.log_message, f"[{m.id}] [ERR] Reset failed: {e}")
        finally:
            self.call_from_thread(self.set_job_status, "IDLE")
        self.call_from_thread(self.action_refresh)

    @work(thread=True)
    def action_stop_selected(self) -> None:
        """Stop running distro."""
        if not self.selected_manifest:
            return
        m = self.selected_manifest
        self.call_from_thread(self.set_job_status, f"STOPPING {m.id}...")
        self.call_from_thread(self.log_message, f"[{m.id}] Stopping distro '{m.distro_name}'...")
        try:
            self.engine.stop_lab(
                manifest=m,
                progress_callback=lambda msg: self.call_from_thread(self.log_message, f"  {msg}"),
            )
            self.call_from_thread(self.log_message, f"[{m.id}] Distro '{m.distro_name}' stopped.")
        except Exception as e:
            self.call_from_thread(self.log_message, f"[{m.id}] [ERR] Stop failed: {e}")
        finally:
            self.call_from_thread(self.set_job_status, "IDLE")
        self.call_from_thread(self.action_refresh)

    def action_open_generate(self) -> None:
        """Open the AI lab generation modal."""
        def handle_generate(res: Optional[Tuple[str, str, str]]) -> None:
            if res:
                domain, topic, base_image = res
                self._run_generate_worker(domain, topic, base_image)

        self.push_screen(GenerateModal(), handle_generate)

    @work(thread=True)
    def _run_generate_worker(self, domain: str, topic: str, base_image: str) -> None:
        """Background AI generator worker."""
        self.call_from_thread(self.set_job_status, "GENERATING AI LAB...")
        self.call_from_thread(self._switch_to_tab, "tab-logs")
        self.call_from_thread(
            self.log_message,
            f"[AI] Requesting scenario generation for {domain}: '{topic}' ({base_image})..."
        )
        generator = AILabGenerator(self.config.ai)
        try:
            payload = generator.generate_lab(
                domain=domain,
                topic=topic,
                base_image=base_image,
                progress_callback=lambda msg: self.call_from_thread(self.log_message, f"[AI] {msg}"),
            )
            saved_dir = generator.save_generated_lab(
                payload,
                self.config.labs_dir,
                progress_callback=lambda msg: self.call_from_thread(self.log_message, f"[AI] {msg}"),
            )
            self.call_from_thread(
                self.log_message,
                f"[AI] [OK] Successfully generated and saved lab to {saved_dir.name}."
            )
            self.call_from_thread(self.action_refresh)
        except Exception as e:
            self.call_from_thread(self.log_message, f"[AI] [ERR] Generation failed: {e}")
        finally:
            self.call_from_thread(self.set_job_status, "IDLE")
