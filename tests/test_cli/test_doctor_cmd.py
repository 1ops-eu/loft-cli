"""CLI tests for the doctor command — agent install fallback behaviour."""

from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from loft_cli.cli import app

runner = CliRunner()


def _make_transport_mock(agent_installed: bool):
    """Return a mock FabricTransport that simulates a server (with or without agent)."""
    from loft_cli.runtime.ssh import CommandResult

    transport = MagicMock()
    transport.test_connection.return_value = True

    if agent_installed:
        transport.run.return_value = CommandResult(
            ok=True, stdout="loft-cli-agent 0.6.3", stderr="", return_code=0
        )
    else:
        transport.run.return_value = CommandResult(
            ok=False, stdout="", stderr="not found", return_code=127
        )
    transport.close.return_value = None
    return transport


@pytest.mark.usefixtures("_load_loft_cli_addons")
def test_doctor_exits_when_agent_missing_and_install_fails(bootstrap_yaml, mocker):
    """doctor exits with code 1 when agent is absent and auto-install fails."""
    transport_mock = _make_transport_mock(agent_installed=False)

    # FabricTransport is imported lazily inside the doctor function; patch it at source
    mocker.patch(
        "loft_cli.runtime.fabric_transport.FabricTransport",
        return_value=transport_mock,
    )
    # update_agent is imported lazily inside the `if not agent_version` block;
    # patch it at source so the lazy import resolves to our mock
    mocker.patch("loft_cli.updater.update_agent", return_value=False)
    # detect_agent is imported lazily; patch at source
    mocker.patch("loft_cli.agent_installer.detect_agent", return_value=None)

    result = runner.invoke(app, ["doctor", str(bootstrap_yaml)])

    assert result.exit_code != 0
    # Should mention auto-install failure
    assert "auto-install failed" in result.output or "agent-update" in result.output


@pytest.mark.usefixtures("_load_loft_cli_addons")
def test_doctor_shows_autoinstall_message_when_agent_missing(bootstrap_yaml, mocker):
    """doctor prints auto-install message when agent is not present."""
    transport_mock = _make_transport_mock(agent_installed=False)

    mocker.patch(
        "loft_cli.runtime.fabric_transport.FabricTransport",
        return_value=transport_mock,
    )
    mocker.patch("loft_cli.updater.update_agent", return_value=False)
    mocker.patch("loft_cli.agent_installer.detect_agent", return_value=None)

    result = runner.invoke(app, ["doctor", str(bootstrap_yaml)])

    assert "attempting automatic install" in result.output


@pytest.mark.usefixtures("_load_loft_cli_addons")
def test_update_agent_falls_back_to_local_binary(tmp_path, mocker):
    """update_agent falls back to local binary when GitHub release unavailable."""
    from loft_cli.runtime.ssh import CommandResult
    from loft_cli.updater import update_agent

    # Mock transport
    transport_mock = MagicMock()
    transport_mock.run.return_value = CommandResult(
        ok=True, stdout="x86_64", stderr="", return_code=0
    )
    transport_mock.upload.return_value = None

    # detect_agent: first call (current version check) → None, second call (verify) → "0.6.3"
    detect_calls = {"n": 0}

    def _detect(t):
        detect_calls["n"] += 1
        if detect_calls["n"] == 1:
            return None
        return "0.6.3"

    # detect_agent is imported inside update_agent; patch at source
    mocker.patch("loft_cli.agent_installer.detect_agent", side_effect=_detect)

    # GitHub release unavailable
    mocker.patch(
        "loft_cli.updater.get_latest_release",
        side_effect=Exception("network error"),
    )

    # Local binary available
    local_bin = tmp_path / "loft-cli-agent"
    local_bin.write_bytes(b"\x7fELF")  # dummy binary
    local_bin.chmod(0o755)
    # get_local_agent_binary is imported inside update_agent; patch at source
    mocker.patch("loft_cli.agent_installer.get_local_agent_binary", return_value=local_bin)

    from rich.console import Console

    console = Console(quiet=True)
    result = update_agent(transport_mock, console=console)

    assert result is True
    transport_mock.upload.assert_called_once()


@pytest.mark.usefixtures("_load_loft_cli_addons")
def test_update_agent_fails_gracefully_when_no_binary_available(mocker):
    """update_agent returns False (not raises) when no binary is available anywhere."""
    from loft_cli.runtime.ssh import CommandResult
    from loft_cli.updater import update_agent

    transport_mock = MagicMock()
    transport_mock.run.return_value = CommandResult(
        ok=False, stdout="", stderr="not found", return_code=127
    )

    mocker.patch("loft_cli.agent_installer.detect_agent", return_value=None)
    mocker.patch(
        "loft_cli.updater.get_latest_release",
        side_effect=Exception("network error"),
    )
    mocker.patch("loft_cli.agent_installer.get_local_agent_binary", return_value=None)

    from rich.console import Console

    console = Console(quiet=True)
    result = update_agent(transport_mock, console=console)

    assert result is False
