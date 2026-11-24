"""Headless UI tests for Textual TUI."""

from unittest.mock import MagicMock, patch
import pytest
from textual.widgets import Button, DataTable, Input, Markdown, Static, TabbedContent

from lplab.config import load_config
from lplab.tui import GenerateModal, LabEngineApp


@pytest.mark.asyncio
async def test_tui_loads_all_nine_labs_and_updates_views():
    """Verify all 9 labs load in DataTable and selecting updates banner and brief."""
    config = load_config()
    app = LabEngineApp(config=config)

    async with app.run_test() as pilot:
        table = app.query_one("#labs-table", DataTable)
        assert table.row_count == 9

        banner = app.query_one("#lab-header-banner", Static)
        work_order = app.query_one("#work-order-markdown", Markdown)

        # 1. Select lab-02
        app.select_lab_by_id("lab-02")
        await pilot.pause(0.1)

        assert app.selected_manifest is not None
        assert app.selected_manifest.id == "lab-02"
        banner_text = str(banner.render())
        assert "lab-02" in banner_text

        # Verify Work Order content updated for lab-02
        assert "api.lab.internal" in work_order._markdown

        # 2. Select lab-06
        app.select_lab_by_id("lab-06")
        await pilot.pause()

        assert app.selected_manifest is not None
        assert app.selected_manifest.id == "lab-06"
        banner_text_06 = str(banner.render())
        assert "lab-06" in banner_text_06
        assert "18443" in work_order._markdown or "nginx" in work_order._markdown

        # 3. Select lab-09
        app.select_lab_by_id("lab-09")
        await pilot.pause()

        assert app.selected_manifest is not None
        assert app.selected_manifest.id == "lab-09"
        banner_text_09 = str(banner.render())
        assert "lab-09" in banner_text_09
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
    """Verify clicking 'Launch Lab' button invokes start_lab for the selected lab (lab-02, not lab-01)."""
    config = load_config()
    app = LabEngineApp(config=config)

    async with app.run_test() as pilot:
        # Select lab-02
        app.select_lab_by_id("lab-02")
        await pilot.pause()
        assert app.selected_manifest.id == "lab-02"

        with patch.object(app.engine, "start_lab") as mock_start:
            # Click the 'Launch Lab [Enter]' action bar button
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
