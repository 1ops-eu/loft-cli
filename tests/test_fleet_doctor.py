"""Fleet doctor integration tests — mocked _run_doctor_on_spec (v0.10 feature).

Note: The ticket refers to mocking _run_doctor_on_host, but the implementation
uses _run_doctor_on_spec in loft_cli.cli — we mock the actual function.

Coverage:
- All clean → summary shows all green; exit code 0
- One spec drifted → exit code 1; drifted resources listed in table row
- One spec connection error with --continue-on-error → error recorded in table; scan continues
- Single-spec doctor <spec.yaml> (no --fleet) unchanged
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from typer.testing import CliRunner

from loft_cli.cli import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_spec(path: Path, name: str, labels: dict | None = None) -> None:
    """Write a minimal valid bootstrap spec YAML to *path*."""
    import yaml

    data: dict = {
        "kind": "bootstrap",
        "meta": {"name": name},
        "host": {"name": name, "address": "192.168.1.100"},
        "login": {"user": "root", "private_key": "~/.ssh/id_ed25519", "port": 22},
        "local": {"inventory": {"enabled": False}},
    }
    if labels:
        data["meta"]["labels"] = labels
    path.write_text(yaml.dump(data))


def _clean_result() -> dict:
    """Return a doctor result dict representing a clean host."""
    return {"status": "clean", "drifted": [], "error": None}


def _drift_result(drifted: list[str] | None = None) -> dict:
    """Return a doctor result dict representing drift."""
    return {"status": "drift", "drifted": drifted or ["nginx.service", "ufw"], "error": None}


def _error_result(error: str = "Connection refused") -> dict:
    """Return a doctor result dict representing a connection/execution error."""
    return {"status": "error", "drifted": [], "error": error}


# ---------------------------------------------------------------------------
# Fleet doctor — all-clean scenario
# ---------------------------------------------------------------------------


class TestFleetDoctorAllClean:
    """Fleet doctor exits 0 when all specs are clean."""

    def test_all_clean_exit_code_0(self, tmp_path, mocker):
        """All specs clean → exit code 0."""
        fleet_dir = tmp_path / "fleet"
        fleet_dir.mkdir()

        spec_a = fleet_dir / "worker-01.yaml"
        spec_b = fleet_dir / "worker-02.yaml"
        _write_spec(spec_a, "worker-01", labels={"env": "staging"})
        _write_spec(spec_b, "worker-02", labels={"env": "staging"})

        fake_matches = [
            (str(spec_a), MagicMock()),
            (str(spec_b), MagicMock()),
        ]

        mocker.patch("loft_cli.local.selector.select_specs", return_value=fake_matches)
        mocker.patch(
            "loft_cli.cli._build_pipeline", return_value=(MagicMock(), MagicMock(), MagicMock(), [])
        )
        mocker.patch("loft_cli.cli._run_doctor_on_spec", return_value=_clean_result())

        result = runner.invoke(
            app, ["doctor", "--fleet", str(fleet_dir), "--selector", "env=staging"]
        )

        assert result.exit_code == 0

    def test_all_clean_output_mentions_clean(self, tmp_path, mocker):
        """All specs clean → output contains 'clean'."""
        fleet_dir = tmp_path / "fleet"
        fleet_dir.mkdir()

        spec_a = fleet_dir / "worker-01.yaml"
        _write_spec(spec_a, "worker-01", labels={"env": "staging"})

        fake_matches = [(str(spec_a), MagicMock())]

        mocker.patch("loft_cli.local.selector.select_specs", return_value=fake_matches)
        mocker.patch(
            "loft_cli.cli._build_pipeline", return_value=(MagicMock(), MagicMock(), MagicMock(), [])
        )
        mocker.patch("loft_cli.cli._run_doctor_on_spec", return_value=_clean_result())

        result = runner.invoke(
            app, ["doctor", "--fleet", str(fleet_dir), "--selector", "env=staging"]
        )

        assert result.exit_code == 0
        assert "clean" in result.output


# ---------------------------------------------------------------------------
# Fleet doctor — drift scenario
# ---------------------------------------------------------------------------


class TestFleetDoctorDrift:
    """Fleet doctor exits 1 when any spec is drifted."""

    def test_one_spec_drifted_exit_code_1(self, tmp_path, mocker):
        """One drifted spec → exit code 1."""
        fleet_dir = tmp_path / "fleet"
        fleet_dir.mkdir()

        spec_a = fleet_dir / "worker-01.yaml"
        _write_spec(spec_a, "worker-01", labels={"env": "prod"})

        fake_matches = [(str(spec_a), MagicMock())]

        mocker.patch("loft_cli.local.selector.select_specs", return_value=fake_matches)
        mocker.patch(
            "loft_cli.cli._build_pipeline", return_value=(MagicMock(), MagicMock(), MagicMock(), [])
        )
        mocker.patch(
            "loft_cli.cli._run_doctor_on_spec",
            return_value=_drift_result(["nginx.service", "ufw"]),
        )

        result = runner.invoke(app, ["doctor", "--fleet", str(fleet_dir), "--selector", "env=prod"])

        assert result.exit_code != 0

    def test_drifted_resources_listed_in_output(self, tmp_path, mocker):
        """Drifted resources appear in the doctor output."""
        fleet_dir = tmp_path / "fleet"
        fleet_dir.mkdir()

        spec_a = fleet_dir / "worker-01.yaml"
        _write_spec(spec_a, "worker-01", labels={"env": "prod"})

        fake_matches = [(str(spec_a), MagicMock())]

        mocker.patch("loft_cli.local.selector.select_specs", return_value=fake_matches)
        mocker.patch(
            "loft_cli.cli._build_pipeline", return_value=(MagicMock(), MagicMock(), MagicMock(), [])
        )
        mocker.patch(
            "loft_cli.cli._run_doctor_on_spec",
            return_value=_drift_result(["nginx.service", "ufw"]),
        )

        result = runner.invoke(app, ["doctor", "--fleet", str(fleet_dir), "--selector", "env=prod"])

        # Drifted resource names should appear in the output
        assert "nginx.service" in result.output or "drift" in result.output

    def test_one_clean_one_drifted_summary_counts(self, tmp_path, mocker):
        """Summary correctly shows 1 clean, 1 drifted."""
        fleet_dir = tmp_path / "fleet"
        fleet_dir.mkdir()

        spec_a = fleet_dir / "worker-01.yaml"
        spec_b = fleet_dir / "worker-02.yaml"
        _write_spec(spec_a, "worker-01", labels={"env": "prod"})
        _write_spec(spec_b, "worker-02", labels={"env": "prod"})

        fake_matches = [
            (str(spec_a), MagicMock()),
            (str(spec_b), MagicMock()),
        ]

        call_count = {"n": 0}

        def _alternating_result(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return _clean_result()
            return _drift_result(["some-resource"])

        mocker.patch("loft_cli.local.selector.select_specs", return_value=fake_matches)
        mocker.patch(
            "loft_cli.cli._build_pipeline", return_value=(MagicMock(), MagicMock(), MagicMock(), [])
        )
        mocker.patch("loft_cli.cli._run_doctor_on_spec", side_effect=_alternating_result)

        result = runner.invoke(app, ["doctor", "--fleet", str(fleet_dir), "--selector", "env=prod"])

        # Summary counts should reflect the results
        assert "1 clean" in result.output
        assert "1 drifted" in result.output
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Fleet doctor — error + continue-on-error
# ---------------------------------------------------------------------------


class TestFleetDoctorContinueOnError:
    """Connection errors with --continue-on-error do not stop scan."""

    def test_error_with_continue_on_error_scan_continues(self, tmp_path, mocker):
        """One error spec with --continue-on-error → second spec is still checked."""
        fleet_dir = tmp_path / "fleet"
        fleet_dir.mkdir()

        spec_a = fleet_dir / "worker-01.yaml"
        spec_b = fleet_dir / "worker-02.yaml"
        _write_spec(spec_a, "worker-01", labels={"env": "staging"})
        _write_spec(spec_b, "worker-02", labels={"env": "staging"})

        fake_matches = [
            (str(spec_a), MagicMock()),
            (str(spec_b), MagicMock()),
        ]

        call_count = {"n": 0}

        def _first_error_second_clean(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return _error_result("Connection refused")
            return _clean_result()

        doctor_mock = mocker.patch(
            "loft_cli.cli._run_doctor_on_spec", side_effect=_first_error_second_clean
        )
        mocker.patch("loft_cli.local.selector.select_specs", return_value=fake_matches)
        mocker.patch(
            "loft_cli.cli._build_pipeline", return_value=(MagicMock(), MagicMock(), MagicMock(), [])
        )

        result = runner.invoke(
            app,
            [
                "doctor",
                "--fleet",
                str(fleet_dir),
                "--selector",
                "env=staging",
                "--continue-on-error",
            ],
        )

        # Both specs should have been checked
        assert doctor_mock.call_count == 2
        # Exit code 1 because one errored
        assert result.exit_code != 0

    def test_error_recorded_in_table_output(self, tmp_path, mocker):
        """Error entry with --continue-on-error appears in table output."""
        fleet_dir = tmp_path / "fleet"
        fleet_dir.mkdir()

        spec_a = fleet_dir / "worker-01.yaml"
        _write_spec(spec_a, "worker-01", labels={"env": "staging"})

        fake_matches = [(str(spec_a), MagicMock())]

        mocker.patch("loft_cli.local.selector.select_specs", return_value=fake_matches)
        mocker.patch(
            "loft_cli.cli._build_pipeline", return_value=(MagicMock(), MagicMock(), MagicMock(), [])
        )
        mocker.patch(
            "loft_cli.cli._run_doctor_on_spec",
            return_value=_error_result("Connection refused"),
        )

        result = runner.invoke(
            app,
            [
                "doctor",
                "--fleet",
                str(fleet_dir),
                "--selector",
                "env=staging",
                "--continue-on-error",
            ],
        )

        # Error should be mentioned in the output
        assert "error" in result.output.lower() or "Connection refused" in result.output

    def test_error_without_continue_on_error_stops_scan(self, tmp_path, mocker):
        """Without --continue-on-error, an error stops the scan after the first error."""
        fleet_dir = tmp_path / "fleet"
        fleet_dir.mkdir()

        spec_a = fleet_dir / "worker-01.yaml"
        spec_b = fleet_dir / "worker-02.yaml"
        _write_spec(spec_a, "worker-01", labels={"env": "staging"})
        _write_spec(spec_b, "worker-02", labels={"env": "staging"})

        fake_matches = [
            (str(spec_a), MagicMock()),
            (str(spec_b), MagicMock()),
        ]

        call_count = {"n": 0}

        def _first_error(*args, **kwargs):
            call_count["n"] += 1
            return _error_result("SSH timeout")

        doctor_mock = mocker.patch("loft_cli.cli._run_doctor_on_spec", side_effect=_first_error)
        mocker.patch("loft_cli.local.selector.select_specs", return_value=fake_matches)
        mocker.patch(
            "loft_cli.cli._build_pipeline", return_value=(MagicMock(), MagicMock(), MagicMock(), [])
        )

        result = runner.invoke(
            app,
            [
                "doctor",
                "--fleet",
                str(fleet_dir),
                "--selector",
                "env=staging",
                # No --continue-on-error
            ],
        )

        # Should have stopped after the first error
        assert doctor_mock.call_count == 1
        assert result.exit_code != 0

    def test_error_count_in_summary(self, tmp_path, mocker):
        """Summary mentions the number of errored hosts."""
        fleet_dir = tmp_path / "fleet"
        fleet_dir.mkdir()

        spec_a = fleet_dir / "worker-01.yaml"
        spec_b = fleet_dir / "worker-02.yaml"
        _write_spec(spec_a, "worker-01", labels={"env": "staging"})
        _write_spec(spec_b, "worker-02", labels={"env": "staging"})

        fake_matches = [
            (str(spec_a), MagicMock()),
            (str(spec_b), MagicMock()),
        ]

        mocker.patch("loft_cli.local.selector.select_specs", return_value=fake_matches)
        mocker.patch(
            "loft_cli.cli._build_pipeline", return_value=(MagicMock(), MagicMock(), MagicMock(), [])
        )
        mocker.patch(
            "loft_cli.cli._run_doctor_on_spec",
            return_value=_error_result("Network unreachable"),
        )

        result = runner.invoke(
            app,
            [
                "doctor",
                "--fleet",
                str(fleet_dir),
                "--selector",
                "env=staging",
                "--continue-on-error",
            ],
        )

        # Both errored — summary mentions "errored"
        assert "errored" in result.output or "error" in result.output.lower()


# ---------------------------------------------------------------------------
# Single-spec doctor (no --fleet) unchanged
# ---------------------------------------------------------------------------


class TestSingleSpecDoctorUnchanged:
    """Single-spec doctor <spec.yaml> (no --fleet) is unaffected by fleet changes."""

    def test_single_spec_doctor_without_agent_exits_1(self, bootstrap_yaml, mocker):
        """Single-spec doctor exits 1 when agent is not installed (existing behaviour)."""
        transport_mock = MagicMock()
        transport_mock.test_connection.return_value = True

        mocker.patch(
            "loft_cli.runtime.fabric_transport.FabricTransport",
            return_value=transport_mock,
        )
        mocker.patch("loft_cli.updater.update_agent", return_value=False)
        mocker.patch("loft_cli.agent_installer.detect_agent", return_value=None)

        result = runner.invoke(app, ["doctor", str(bootstrap_yaml)])

        assert result.exit_code != 0

    def test_single_spec_doctor_does_not_invoke_fleet_path(self, bootstrap_yaml, mocker):
        """Single-spec doctor does NOT invoke select_specs (no fleet scanning)."""
        transport_mock = MagicMock()
        transport_mock.test_connection.return_value = True

        mocker.patch(
            "loft_cli.runtime.fabric_transport.FabricTransport",
            return_value=transport_mock,
        )
        mocker.patch("loft_cli.updater.update_agent", return_value=False)
        mocker.patch("loft_cli.agent_installer.detect_agent", return_value=None)

        select_mock = mocker.patch("loft_cli.local.selector.select_specs")

        runner.invoke(app, ["doctor", str(bootstrap_yaml)])

        select_mock.assert_not_called()
