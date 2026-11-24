"""Headless UI tests for Textual TUI."""

from unittest.mock import MagicMock, patch
import pytest
from textual.widgets import Button, DataTable, Input, Markdown, RichLog, Static, TabbedContent

from lplab.config import load_config
from lplab.tui import GenerateModal, LabEngineApp


@pytest.mark.asyncio
async def test_tui_loads_all_nine_labs_and_updates_views():
    """Verify all 9 labs load in DataTable and selecting updates banner, brief, and acceptance criteria."""
    config = load_config()
    app = LabEngineApp(config=config)

    async with app.run_test() as pilot:
        table = app.query_one("#labs-table", DataTable)
        assert table.row_count == 9

        banner = app.query_one("#lab-header-banner", Static)
        work_order = app.query_one("#work-order-markdown", Markdown)
        verify_widget = app.query_one("#verify-content", Static)

        # 1. Select lab-02
        await app.select_lab_by_id("lab-02")
        await pilot.pause(0.1)

        assert app.selected_manifest is not None
        assert app.selected_manifest.id == "lab-02"
        banner_text = str(banner.render())
        assert "LAB-02" in banner_text

        # Verify Work Order content updated for lab-02
        assert "api.lab.internal" in work_order._markdown

        # Verify Acceptance Criteria / Objectives updated for lab-02
        verify_text = str(verify_widget.render())
        assert "ACCEPTANCE CRITERIA / OBJECTIVES" in verify_text

        # 2. Select lab-06
        await app.select_lab_by_id("lab-06")
        await pilot.pause(0.1)

        assert app.selected_manifest is not None
        assert app.selected_manifest.id == "lab-06"
        banner_text_06 = str(banner.render())
        assert "LAB-06" in banner_text_06
        assert "18443" in work_order._markdown or "nginx" in work_order._markdown

        # 3. Select lab-09
        await app.select_lab_by_id("lab-09")
        await pilot.pause(0.1)

        assert app.selected_manifest is not None
        assert app.selected_manifest.id == "lab-09"
        banner_text_09 = str(banner.render())
        assert "LAB-09" in banner_text_09
        assert "archive" in work_order._markdown


@pytest.mark.asyncio
async def test_tui_modal_keystroke_isolation_and_escape():
    """Verify typing in GenerateModal input does not trigger app keybindings, and escape cancels."""
    config = load_config()
    app = LabEngineApp(config=config)

    async with app.run_test() as pilot:
        # Press 'g' to open GenerateModal
        await pilot.press("g")
        await pilot.pause()

        assert isinstance(app.screen, GenerateModal)

        input_widget = app.screen.query_one("#input-topic", Input)
        input_widget.focus()
        await pilot.pause()

        # Type 'fix q v r s g' - none of these single keys should quit or trigger actions
        for char in "fix q v r s g":
            await pilot.press(char)
        await pilot.pause()

        assert isinstance(app.screen, GenerateModal)
        assert input_widget.value == "fix q v r s g"

        # Press escape to dismiss modal
        await pilot.press("escape")
        await pilot.pause()

        assert not isinstance(app.screen, GenerateModal)


@pytest.mark.asyncio
async def test_tui_action_bar_launch_button_starts_selected_lab():
    """Verify clicking 'Launch [Enter]' button invokes start_lab for the selected lab (lab-02, not lab-01)."""
    config = load_config()
    app = LabEngineApp(config=config)

    async with app.run_test() as pilot:
        # Select lab-02
        await app.select_lab_by_id("lab-02")
        await pilot.pause(0.1)
        assert app.selected_manifest.id == "lab-02"

        with patch.object(app.engine, "start_lab") as mock_start:
            # Click the 'Launch [Enter]' action bar button
            await pilot.click("#btn-action-start")
            await pilot.pause(0.2)

            assert mock_start.called
            called_manifest = (
                mock_start.call_args.kwargs.get("manifest")
                if mock_start.call_args.kwargs and "manifest" in mock_start.call_args.kwargs
                else mock_start.call_args[0][0]
            )
            assert called_manifest.id == "lab-02"
            assert called_manifest.distro_name == "lplab-lab-02-networking-firewall"


@pytest.mark.asyncio
async def test_tui_logging_worker_populates_richlog_and_history():
    """Verify logging populates in-memory log_history and RichLog widget safely."""
    config = load_config()
    app = LabEngineApp(config=config)

    async with app.run_test() as pilot:
        app._switch_to_tab("tab-logs")
        await pilot.pause(0.1)

        app.log_message("Test worker log line 1")
        app.log_message("Test worker log line 2")
        await pilot.pause(0.1)

        assert "Test worker log line 1" in app.log_history
        assert "Test worker log line 2" in app.log_history

        log_widget = app.query_one("#log-view", RichLog)
        assert len(log_widget.lines) >= 2
