"""Textual TUI for browsing, provisioning, launching, and verifying Linux+ labs."""

from pathlib import Path
import time
from typing import Dict, List, Optional, Tuple
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
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
    """Confirmation modal before wiping and resetting a lab."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    ResetConfirmModal {
        align: center middle;
    }
    #confirm-dialog {
        padding: 1 2;
        width: 60;
        height: auto;
        border: thick $warning;
        background: $surface;
    }
    #confirm-buttons {
        margin-top: 1;
        align: right middle;
    }
    Button {
        margin-left: 2;
    }
    """

    def __init__(self, lab_title: str):
        super().__init__()
        self.lab_title = lab_title

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("[bold yellow]Confirm Lab Reset[/bold yellow]\n"),
            Label(f"Are you sure you want to completely wipe and rebuild:\n[cyan]{self.lab_title}[/cyan]?\n"),
            Label("[dim]All files, configurations, and progress will be permanently erased.[/dim]"),
            Horizontal(
                Button("Cancel", variant="default", id="btn-cancel"),
                Button("Reset Lab", variant="error", id="btn-reset"),
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
    """Modal dialog for generating a new AI lab scenario."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    GenerateModal {
        align: center middle;
    }
    #gen-dialog {
        padding: 1 2;
        width: 70;
        height: auto;
        border: thick $primary;
        background: $surface;
    }
    .form-item {
        margin-bottom: 1;
    }
    #gen-buttons {
        margin-top: 1;
        align: right middle;
    }
    Button {
        margin-left: 2;
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
            Label("[bold green]Generate AI CompTIA Linux+ Lab[/bold green]\n"),
            Label("Domain:"),
            Select(self.DOMAINS, value="system_management", id="select-domain", classes="form-item"),
            Label("Topic / Scenario Concept:"),
            Input(placeholder="e.g. LVM snapshot volume recovery or SSH hardening", id="input-topic", classes="form-item"),
            Label("Base Distro:"),
            Select(self.IMAGES, value="rockylinux-9", id="select-image", classes="form-item"),
            Horizontal(
                Button("Cancel", variant="default", id="btn-cancel"),
                Button("Generate Lab", variant="success", id="btn-generate"),
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
    """Textual split-pane launcher UI for Linux+ WSL Lab Engine."""

    TITLE = "lplab - Linux+ WSL Lab Engine"
    SUB_TITLE = "CompTIA Linux+ (XK0-006) Hands-On Practice"

    # Single-key bindings do NOT use priority=True so inputs in modals are never intercepted
    BINDINGS = [
        Binding("enter", "start_selected", "Launch Lab"),
        Binding("v", "verify_selected", "Verify"),
        Binding("r", "reset_selected", "Reset"),
        Binding("s", "stop_selected", "Stop"),
        Binding("g", "open_generate", "Generate Lab"),
        Binding("q", "quit", "Quit"),
    ]

    CSS = """
    Screen {
        layout: vertical;
    }
    #main-container {
        layout: horizontal;
        height: 1fr;
    }
    #left-pane {
        width: 36%;
        height: 100%;
        border-right: heavy $primary-background;
    }
    #right-pane {
        width: 64%;
        height: 100%;
        layout: vertical;
    }
    #lab-header-banner {
        height: auto;
        padding: 1 2;
        background: $boost;
        border-bottom: solid $primary;
    }
    #action-bar {
        height: auto;
        padding: 0 1;
        margin-top: 1;
        margin-bottom: 1;
    }
    #action-bar Button {
        margin-right: 1;
    }
    DataTable {
        height: 100%;
    }
    #tabbed-content {
        height: 1fr;
    }
    #work-order-markdown {
        padding: 1 2;
        height: 100%;
        overflow-y: scroll;
    }
    #verify-content {
        padding: 1 2;
        height: 100%;
        overflow-y: scroll;
    }
    RichLog {
        height: 100%;
        border: none;
        background: $surface;
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

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="main-container"):
            with Vertical(id="left-pane"):
                yield DataTable(id="labs-table", cursor_type="row")
            with Vertical(id="right-pane"):
                yield Static(id="lab-header-banner")
                with Horizontal(id="action-bar"):
                    yield Button("Launch Lab [Enter]", variant="success", id="btn-action-start")
                    yield Button("Verify [v]", variant="primary", id="btn-action-verify")
                    yield Button("Stop [s]", variant="default", id="btn-action-stop")
                    yield Button("Reset [r]", variant="warning", id="btn-action-reset")
                    yield Button("New AI Lab [g]", variant="default", id="btn-action-generate")
                with TabbedContent(initial="tab-brief", id="tabbed-content"):
                    with TabPane("Work Order", id="tab-brief"):
                        yield Markdown(id="work-order-markdown")
                    with TabPane("Verification", id="tab-verify"):
                        yield Static(id="verify-content")
                    with TabPane("Logs", id="tab-logs"):
                        yield RichLog(id="log-view", highlight=True, markup=True)
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#labs-table", DataTable)
        table.add_columns("ID", "Title", "Base", "Status")
        self.refresh_labs()

    def log_message(self, message: str) -> None:
        """Post a line to the live Logs tab."""
        log_view = self.query_one("#log-view", RichLog)
        log_view.write(message)

    def _switch_to_tab(self, tab_id: str) -> None:
        """Helper to switch active tab in right pane."""
        tabbed = self.query_one("#tabbed-content", TabbedContent)
        tabbed.active = tab_id

    def format_badge(self, status: LabRuntimeStatus, record: Optional[LabStateRecord]) -> str:
        """Format live status badge for table view and banner."""
        if status == LabRuntimeStatus.NOT_PROVISIONED:
            return "[bold yellow][NEW][/bold yellow]"
        elif status == LabRuntimeStatus.RUNNING:
            return "[bold green][RUNNING][/bold green]"
        elif status == LabRuntimeStatus.STOPPED:
            return "[dim][STOPPED][/dim]"
        elif status == LabRuntimeStatus.PASSED:
            p = record.score_passed if record else 0
            t = record.score_total if record else 0
            return f"[bold green][PASS {p}/{t}][/bold green]"
        elif status == LabRuntimeStatus.FAILED:
            p = record.score_passed if record else 0
            t = record.score_total if record else 0
            return f"[bold red][FAIL {p}/{t}][/bold red]"
        return f"[{status.value}]"

    def refresh_labs(self) -> None:
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
            self.update_details_view()

    def select_lab_by_id(self, lab_id: str) -> None:
        """Select a lab by ID and update views."""
        for m, p in self.labs:
            if m.id == lab_id:
                self.selected_manifest = m
                self.selected_path = p
                self.update_details_view()
                break

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle Enter key or double-click on a table row to select and launch."""
        row_key = event.row_key.value
        self.select_lab_by_id(row_key)
        self.action_start_selected()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Handle keyboard arrow navigation or single click."""
        if event.row_key:
            row_key = event.row_key.value
            self.select_lab_by_id(row_key)

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
        """Update top banner of selected lab."""
        banner = self.query_one("#lab-header-banner", Static)
        if not self.selected_manifest:
            banner.update("[dim]No lab selected[/dim]")
            return
        status, record = self.engine.get_lab_status(self.selected_manifest)
        badge = self.format_badge(status, record)
        banner.update(
            f"[bold cyan]{self.selected_manifest.id}[/bold cyan] — [bold white]{self.selected_manifest.title}[/bold white]\n"
            f"[dim]WSL Distro:[/dim] [magenta]{self.selected_manifest.distro_name}[/magenta]  "
            f"[dim]Base Image:[/dim] [yellow]{self.selected_manifest.base_image}[/yellow]  "
            f"[dim]Status:[/dim] {badge}"
        )

    def update_details_view(self) -> None:
        """Update right-pane Banner, Work Order, and Verification tabs."""
        if not self.selected_manifest or not self.selected_path:
            return

        # 1. Update Header Banner
        self.update_header_banner()

        # 2. Update Work Order
        brief_file = self.selected_path / "BRIEF.md"
        content = brief_file.read_text(encoding="utf-8") if brief_file.is_file() else "# No Brief Found"
        self.query_one("#work-order-markdown", Markdown).update(content)

        # 3. Update Verification tab from stored state with full check breakdown
        status, record = self.engine.get_lab_status(self.selected_manifest)
        verify_widget = self.query_one("#verify-content", Static)
        if record and record.last_verified:
            v_text = [
                f"[bold cyan]Lab ID:[/bold cyan] {record.lab_id}",
                f"[bold cyan]Last Verification:[/bold cyan] {record.last_verified}",
                f"[bold cyan]Status:[/bold cyan] {record.status.value}",
                f"[bold cyan]Score:[/bold cyan] {record.score_passed} / {record.score_total}\n",
            ]
            if record.checks:
                v_text.append("[bold underline]Per-Check Breakdown:[/bold underline]\n")
                for chk in record.checks:
                    sym = "[bold green]✔ PASS[/bold green]" if chk.passed else "[bold red]✘ FAIL[/bold red]"
                    v_text.append(f"{sym} [bold]{chk.id}[/bold]: {chk.description}")
                    if chk.details:
                        v_text.append(f"   [dim]{chk.details}[/dim]")
                v_text.append("")
            v_text.append("[dim]Press 'v' or click Verify [v] to re-run live checks.[/dim]")
            verify_widget.update("\n".join(v_text))
        else:
            verify_widget.update(
                f"[bold yellow]No verification run yet for {self.selected_manifest.id}.[/bold yellow]\n\n"
                "Press [bold green]'v'[/bold green] or click [bold green]Verify [v][/bold green] to run live system verification checks."
            )

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
        self.call_from_thread(self._switch_to_tab, "tab-logs")
        self.call_from_thread(self.log_message, f"[cyan]Starting lab {m.id}: {m.title}...[/cyan]")
        try:
            self.engine.start_lab(
                manifest=m,
                lab_dir=p,
                progress_callback=lambda msg: self.call_from_thread(self.log_message, f"  {msg}"),
            )
            self.call_from_thread(self.log_message, f"[green]Lab {m.id} launched in terminal.[/green]")
        except Exception as e:
            self.call_from_thread(self.log_message, f"[bold red]Failed to start lab:[/bold red] {e}")
        self.call_from_thread(self.refresh_labs)

    @work(thread=True)
    def action_verify_selected(self) -> None:
        """Execute verify.sh on selected lab in background thread."""
        if not self.selected_manifest or not self.selected_path:
            return
        m = self.selected_manifest
        p = self.selected_path
        self.call_from_thread(self.log_message, f"[cyan]Verifying lab {m.id}...[/cyan]")
        try:
            report: VerifyReport = self.engine.verify_lab(
                manifest=m,
                lab_dir=p,
                progress_callback=lambda msg: self.call_from_thread(self.log_message, f"  {msg}"),
            )
            color = "green" if report.passed else "red"
            msg = (
                f"[bold {color}]Verification {report.lab_id}: "
                f"{'PASSED' if report.passed else 'FAILED'} "
                f"({report.score_passed}/{report.score_total})[/bold {color}]"
            )
            self.call_from_thread(self.log_message, msg)
            for chk in report.checks:
                chk_color = "green" if chk.passed else "red"
                chk_symbol = "✔" if chk.passed else "✘"
                self.call_from_thread(
                    self.log_message,
                    f"  [{chk_color}]{chk_symbol} [{chk.id}] {chk.description}: {chk.details}[/{chk_color}]"
                )

            # Update verification widget & switch tab to verification
            def update_ui() -> None:
                self.update_details_view()
                self._switch_to_tab("tab-verify")

            self.call_from_thread(update_ui)
        except Exception as e:
            self.call_from_thread(self.log_message, f"[bold red]Verification error:[/bold red] {e}")

        self.call_from_thread(self.refresh_labs)

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
        self.call_from_thread(self._switch_to_tab, "tab-logs")
        self.call_from_thread(self.log_message, f"[yellow]Resetting lab {m.id}...[/yellow]")
        try:
            self.engine.reset_lab(
                manifest=m,
                lab_dir=p,
                progress_callback=lambda msg: self.call_from_thread(self.log_message, f"  {msg}"),
            )
            self.call_from_thread(self.log_message, f"[green]Lab {m.id} reset and rebuilt successfully.[/green]")
        except Exception as e:
            self.call_from_thread(self.log_message, f"[bold red]Reset failed:[/bold red] {e}")
        self.call_from_thread(self.refresh_labs)

    @work(thread=True)
    def action_stop_selected(self) -> None:
        """Stop running distro."""
        if not self.selected_manifest:
            return
        m = self.selected_manifest
        self.call_from_thread(self.log_message, f"[yellow]Stopping distro for {m.id}...[/yellow]")
        try:
            self.engine.stop_lab(
                manifest=m,
                progress_callback=lambda msg: self.call_from_thread(self.log_message, f"  {msg}"),
            )
            self.call_from_thread(self.log_message, f"[green]Distro '{m.distro_name}' stopped.[/green]")
        except Exception as e:
            self.call_from_thread(self.log_message, f"[bold red]Stop failed:[/bold red] {e}")
        self.call_from_thread(self.refresh_labs)

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
        self.call_from_thread(self._switch_to_tab, "tab-logs")
        self.call_from_thread(
            self.log_message,
            f"[bold cyan]Requesting AI to generate lab for {domain}: '{topic}' ({base_image})...[/bold cyan]"
        )
        generator = AILabGenerator(self.config.ai)
        try:
            payload = generator.generate_lab(domain=domain, topic=topic, base_image=base_image)
            saved_dir = generator.save_generated_lab(payload, self.config.labs_dir)
            self.call_from_thread(
                self.log_message,
                f"[bold green]Successfully generated and saved lab to {saved_dir.name}![/bold green]"
            )
            self.call_from_thread(self.refresh_labs)
        except Exception as e:
            self.call_from_thread(self.log_message, f"[bold red]AI Generation failed:[/bold red] {e}")
