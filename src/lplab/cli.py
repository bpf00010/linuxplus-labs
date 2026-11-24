"""Command line interface for lplab using Typer and Rich."""

import sys
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import typer

from lplab.ai_generator import AILabGenerator
from lplab.config import load_config
from lplab.lab_engine import LabEngine
from lplab.models import LabRuntimeStatus
from lplab.rootfs_builder import build_rootfs_tar
from lplab.tui import LabEngineApp

app = typer.Typer(
    name="lplab",
    help="Linux+ WSL Lab Engine for CompTIA Linux+ (XK0-006) Hands-On Practice",
    no_args_is_help=False,
)
console = Console()


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    tui: bool = typer.Option(
        False,
        "--tui",
        "-t",
        help="Launch interactive Textual TUI instead of default GUI",
    ),
) -> None:
    """Linux+ WSL Lab Engine for CompTIA Linux+ (XK0-006) Hands-On Practice."""
    if ctx.invoked_subcommand is None:
        if tui:
            ui()
        else:
            gui()


@app.command(name="tui")
def tui_cmd() -> None:
    """Launch the interactive Textual TUI."""
    ui()


@app.command()
def ui() -> None:
    """Launch the interactive Textual TUI."""
    config = load_config()
    tui_app = LabEngineApp(config=config)
    tui_app.run()


@app.command()
def gui(
    browser: bool = typer.Option(
        False,
        "--browser",
        help="Open in default web browser instead of standalone pywebview window",
    ),
    port: Optional[int] = typer.Option(
        None,
        "--port",
        "-p",
        help="Port to bind (defaults to an ephemeral free localhost port)",
    ),
) -> None:
    """Launch the native desktop GUI (FastAPI + uvicorn + pywebview)."""
    from lplab.gui import run_gui
    run_gui(browser=browser, port=port)


@app.command(name="list")
def list_labs() -> None:
    """List all available CompTIA Linux+ labs and their runtime statuses."""
    config = load_config()
    engine = LabEngine(config)
    labs = engine.discover_labs()

    if not labs:
        console.print("[dim]No labs found in[/dim]", config.labs_dir)
        return

    table = Table(title="CompTIA Linux+ (XK0-006) Labs", header_style="bold white", border_style="dim")
    table.add_column("ID", style="bold white", no_wrap=True)
    table.add_column("Title", style="white")
    table.add_column("Base Distro", style="dim")
    table.add_column("Difficulty", style="dim")
    table.add_column("Status", style="bold")
    table.add_column("Score", style="white")
    table.add_column("XK0-006 Domains", style="dim")

    for manifest, _ in labs:
        status, record = engine.get_lab_status(manifest)
        if status == LabRuntimeStatus.NOT_PROVISIONED:
            status_str = "[NEW]"
        elif status == LabRuntimeStatus.RUNNING:
            status_str = "[RUNNING]"
        elif status == LabRuntimeStatus.STOPPED:
            status_str = "[STOPPED]"
        elif status == LabRuntimeStatus.PASSED:
            status_str = "[PASS]"
        elif status == LabRuntimeStatus.FAILED:
            status_str = "[FAIL]"
        else:
            status_str = f"[{status.value.upper()}]"

        score_str = f"{record.score_passed}/{record.score_total}" if record and record.last_verified else "-"
        domains_str = ", ".join(manifest.xk0_006_domains)

        table.add_row(
            manifest.id,
            manifest.title,
            manifest.base_image,
            manifest.difficulty.capitalize(),
            status_str,
            score_str,
            domains_str,
        )

    console.print(table)


@app.command()
def start(lab_id: str) -> None:
    """Provision (if needed) and start an interactive terminal for a lab."""
    config = load_config()
    engine = LabEngine(config)
    lab = engine.get_lab(lab_id)
    if not lab:
        console.print(f"[bold red]Error:[/bold red] Lab '{lab_id}' not found.")
        raise typer.Exit(code=1)

    manifest, path = lab
    console.print(f"[cyan]Starting lab {manifest.id}: {manifest.title}...[/cyan]")
    try:
        engine.start_lab(manifest, path, progress_callback=lambda msg: console.print(f"  {msg}"))
        console.print(f"[bold green]Lab '{manifest.id}' launched successfully.[/bold green]")
    except Exception as e:
        console.print(f"[bold red]Failed to start lab:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def verify(lab_id: str) -> None:
    """Run non-destructive verification checks for a lab."""
    config = load_config()
    engine = LabEngine(config)
    lab = engine.get_lab(lab_id)
    if not lab:
        console.print(f"[bold red]Error:[/bold red] Lab '{lab_id}' not found.")
        raise typer.Exit(code=1)

    manifest, path = lab
    console.print(f"[cyan]Running verification on {manifest.distro_name}...[/cyan]")
    try:
        report = engine.verify_lab(manifest, path, progress_callback=lambda msg: console.print(f"  {msg}"))
    except Exception as e:
        console.print(f"[bold red]Verification error:[/bold red] {e}")
        raise typer.Exit(code=1)

    # Print results table
    t = Table(title=f"Verification Report: {manifest.id} ({manifest.title})", header_style="bold white", border_style="dim")
    t.add_column("Status", justify="center", width=8, style="bold")
    t.add_column("Check ID", style="bold white")
    t.add_column("Description", style="white")
    t.add_column("Details", style="dim")

    for chk in report.checks:
        symbol = "[PASS]" if chk.passed else "[FAIL]"
        t.add_row(symbol, chk.id, chk.description, chk.details)

    console.print(t)
    console.print(
        Panel(
            f"RESULT: {'ALL CHECKS PASSED' if report.passed else 'VERIFICATION FAILED'} "
            f"({report.score_passed} / {report.score_total})",
            expand=False,
            border_style="white" if report.passed else "dim",
        )
    )

    if not report.passed:
        raise typer.Exit(code=1)


@app.command()
def reset(
    lab_id: str,
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Terminate, unregister, and re-provision a lab from scratch."""
    config = load_config()
    engine = LabEngine(config)
    lab = engine.get_lab(lab_id)
    if not lab:
        console.print(f"[bold red]Error:[/bold red] Lab '{lab_id}' not found.")
        raise typer.Exit(code=1)

    manifest, path = lab
    if not yes:
        confirm = typer.confirm(f"Are you sure you want to completely reset and wipe '{manifest.title}'?")
        if not confirm:
            console.print("[dim]Aborted.[/dim]")
            return

    console.print(f"[yellow]Resetting lab {manifest.id}...[/yellow]")
    try:
        engine.reset_lab(manifest, path, progress_callback=lambda msg: console.print(f"  {msg}"))
        console.print(f"[bold green]Lab '{manifest.id}' has been reset and re-provisioned.[/bold green]")
    except Exception as e:
        console.print(f"[bold red]Reset failed:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def stop(lab_id: str) -> None:
    """Terminate the running WSL2 distro for a lab."""
    config = load_config()
    engine = LabEngine(config)
    lab = engine.get_lab(lab_id)
    if not lab:
        console.print(f"[bold red]Error:[/bold red] Lab '{lab_id}' not found.")
        raise typer.Exit(code=1)

    manifest, _ = lab
    console.print(f"[yellow]Stopping {manifest.distro_name}...[/yellow]")
    try:
        engine.stop_lab(manifest, progress_callback=lambda msg: console.print(f"  {msg}"))
        console.print(f"[bold green]Lab '{manifest.id}' stopped.[/bold green]")
    except Exception as e:
        console.print(f"[bold red]Stop failed:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command(name="build-image")
def build_image(
    image: str = typer.Argument("all", help="'rockylinux-9', 'ubuntu-24.04', or 'all'"),
    force: bool = typer.Option(False, "--force", "-f", help="Force rebuild even if cached archive exists"),
) -> None:
    """Build and cache rootfs tarballs using Podman or Docker."""
    config = load_config()
    targets = ["rockylinux-9", "ubuntu-24.04"] if image.lower() == "all" else [image]

    for target in targets:
        console.print(f"[cyan]Building rootfs archive for {target}...[/cyan]")
        try:
            tar_path = build_rootfs_tar(
                base_image=target,
                output_dir=config.base_images_dir,
                force=force,
                progress_callback=lambda msg: console.print(f"  {msg}"),
            )
            console.print(f"[bold green]Done: {tar_path}[/bold green]")
        except Exception as e:
            console.print(f"[bold red]Build error for {target}:[/bold red] {e}")
            raise typer.Exit(code=1)


@app.command()
def generate(
    domain: str = typer.Option("system_management", "--domain", "-d", help="CompTIA Linux+ XK0-006 domain"),
    topic: str = typer.Option("storage-repair", "--topic", "-t", help="Scenario topic"),
    base_image: str = typer.Option("rockylinux-9", "--base-image", "-b", help="rockylinux-9 or ubuntu-24.04"),
) -> None:
    """Generate a new AI lab scenario and run safety linter."""
    config = load_config()
    generator = AILabGenerator(config.ai)
    console.print(f"[cyan]Generating AI lab for {domain}: '{topic}' ({base_image})...[/cyan]")
    try:
        payload = generator.generate_lab(domain=domain, topic=topic, base_image=base_image)
        saved_dir = generator.save_generated_lab(payload, config.labs_dir)
        console.print(f"[bold green]Successfully generated and saved lab to {saved_dir}![/bold green]")
    except Exception as e:
        console.print(f"[bold red]AI Generation failed:[/bold red] {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
