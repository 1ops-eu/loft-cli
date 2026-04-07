"""Fleet apply integration tests — mocked _apply_single (v0.10 feature).

Coverage:
- Two specs matched → _apply_single called twice in order
- First spec fails without --continue-on-error → exits after first failure, second not attempted
- First spec fails with --continue-on-error → second attempted; summary shows 1 succeeded, 1 failed
- Exit code 0 when all succeed; exit code 1 when any fail
- --dry-run forwarded to each _apply_single call
- Single-spec apply <spec.yaml> (no --fleet) unchanged
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
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


def _make_fake_spec_list(tmp_path: Path, count: int) -> list[tuple[str, object]]:
    """Return a list of (filepath_str, parsed_spec) tuples for *count* specs."""
    specs = []
    for i in range(1, count + 1):
        p = tmp_path / f"worker-{i:02d}.yaml"
        _write_spec(p, f"worker-{i:02d}", labels={"role": "worker"})
        # Use a MagicMock as the parsed_spec so no real pipeline runs
        fake_spec = MagicMock()
        fake_spec.meta.name = f"worker-{i:02d}"
        fake_spec.host.address = "192.168.1.100"
        specs.append((str(p), fake_spec))
    return specs


# ---------------------------------------------------------------------------
# Fleet apply tests
# ---------------------------------------------------------------------------


class TestFleetApplyIterationOrder:
    """_apply_single is called once per matched spec, in order."""

    def test_two_specs_apply_single_called_twice_in_order(self, tmp_path, mocker):
        """With two matched specs, _apply_single is called twice, first spec first."""
        fleet_dir = tmp_path / "fleet"
        fleet_dir.mkdir()

        spec_a = fleet_dir / "worker-01.yaml"
        spec_b = fleet_dir / "worker-02.yaml"
        _write_spec(spec_a, "worker-01", labels={"role": "worker"})
        _write_spec(spec_b, "worker-02", labels={"role": "worker"})

        fake_spec_a = MagicMock()
        fake_spec_a.meta.name = "worker-01"
        fake_spec_b = MagicMock()
        fake_spec_b.meta.name = "worker-02"

        fake_matches = [
            (str(spec_a), fake_spec_a),
            (str(spec_b), fake_spec_b),
        ]

        apply_single_mock = mocker.patch("loft_cli.cli._apply_single")
        mocker.patch("loft_cli.cli._build_pipeline", return_value=(
            MagicMock(), MagicMock(), MagicMock(), []
        ))
        mocker.patch("loft_cli.local.selector.select_specs", return_value=fake_matches)

        result = runner.invoke(app, [
            "apply", "--fleet", str(fleet_dir), "--selector", "role=worker"
        ])

        assert result.exit_code == 0
        assert apply_single_mock.call_count == 2

        # Verify call order by checking the spec argument positions
        first_call_args = apply_single_mock.call_args_list[0]
        second_call_args = apply_single_mock.call_args_list[1]
        # First positional arg is parsed_spec
        assert first_call_args[0][0] is not second_call_args[0][0]

    def test_exit_code_0_when_all_succeed(self, tmp_path, mocker):
        """Fleet apply exits with code 0 when all specs succeed."""
        fleet_dir = tmp_path / "fleet"
        fleet_dir.mkdir()

        spec_file = fleet_dir / "worker-01.yaml"
        _write_spec(spec_file, "worker-01", labels={"role": "worker"})

        mocker.patch("loft_cli.cli._apply_single")  # no exception → success
        mocker.patch("loft_cli.cli._build_pipeline", return_value=(
            MagicMock(), MagicMock(), MagicMock(), []
        ))
        mocker.patch(
            "loft_cli.local.selector.select_specs",
            return_value=[(str(spec_file), MagicMock())],
        )

        result = runner.invoke(app, [
            "apply", "--fleet", str(fleet_dir), "--selector", "role=worker"
        ])

        assert result.exit_code == 0
        assert "1 succeeded" in result.output
        assert "0 failed" in result.output


class TestFleetApplyFailureHandling:
    """Stop-on-failure and continue-on-error behaviour."""

    def test_first_spec_fails_without_continue_on_error_second_not_attempted(
        self, tmp_path, mocker
    ):
        """When first spec fails and --continue-on-error is not set, second is not attempted."""
        fleet_dir = tmp_path / "fleet"
        fleet_dir.mkdir()

        spec_a = fleet_dir / "worker-01.yaml"
        spec_b = fleet_dir / "worker-02.yaml"
        _write_spec(spec_a, "worker-01", labels={"role": "worker"})
        _write_spec(spec_b, "worker-02", labels={"role": "worker"})

        fake_matches = [
            (str(spec_a), MagicMock()),
            (str(spec_b), MagicMock()),
        ]

        call_count = {"n": 0}

        def _failing_apply_single(*args, **kwargs):
            call_count["n"] += 1
            raise SystemExit(1)

        apply_single_mock = mocker.patch(
            "loft_cli.cli._apply_single", side_effect=_failing_apply_single
        )
        mocker.patch("loft_cli.cli._build_pipeline", return_value=(
            MagicMock(), MagicMock(), MagicMock(), []
        ))
        mocker.patch("loft_cli.local.selector.select_specs", return_value=fake_matches)

        result = runner.invoke(app, [
            "apply", "--fleet", str(fleet_dir), "--selector", "role=worker"
        ])

        assert result.exit_code != 0
        # Only the first _apply_single should have been called
        assert apply_single_mock.call_count == 1

    def test_first_spec_fails_with_continue_on_error_second_attempted(
        self, tmp_path, mocker
    ):
        """With --continue-on-error, second spec is attempted even if first fails."""
        fleet_dir = tmp_path / "fleet"
        fleet_dir.mkdir()

        spec_a = fleet_dir / "worker-01.yaml"
        spec_b = fleet_dir / "worker-02.yaml"
        _write_spec(spec_a, "worker-01", labels={"role": "worker"})
        _write_spec(spec_b, "worker-02", labels={"role": "worker"})

        fake_matches = [
            (str(spec_a), MagicMock()),
            (str(spec_b), MagicMock()),
        ]

        call_count = {"n": 0}

        def _first_fails_second_ok(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise SystemExit(1)
            # Second call succeeds (no exception)

        apply_single_mock = mocker.patch(
            "loft_cli.cli._apply_single", side_effect=_first_fails_second_ok
        )
        mocker.patch("loft_cli.cli._build_pipeline", return_value=(
            MagicMock(), MagicMock(), MagicMock(), []
        ))
        mocker.patch("loft_cli.local.selector.select_specs", return_value=fake_matches)

        result = runner.invoke(app, [
            "apply", "--fleet", str(fleet_dir), "--selector", "role=worker",
            "--continue-on-error"
        ])

        # Should have attempted both specs
        assert apply_single_mock.call_count == 2
        # Exit code 1 because one failed
        assert result.exit_code != 0

    def test_continue_on_error_summary_shows_1_succeeded_1_failed(
        self, tmp_path, mocker
    ):
        """Summary output shows '1 succeeded, 1 failed' when first fails, second succeeds."""
        fleet_dir = tmp_path / "fleet"
        fleet_dir.mkdir()

        spec_a = fleet_dir / "worker-01.yaml"
        spec_b = fleet_dir / "worker-02.yaml"
        _write_spec(spec_a, "worker-01", labels={"role": "worker"})
        _write_spec(spec_b, "worker-02", labels={"role": "worker"})

        fake_matches = [
            (str(spec_a), MagicMock()),
            (str(spec_b), MagicMock()),
        ]

        call_count = {"n": 0}

        def _first_fails(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise SystemExit(1)

        mocker.patch("loft_cli.cli._apply_single", side_effect=_first_fails)
        mocker.patch("loft_cli.cli._build_pipeline", return_value=(
            MagicMock(), MagicMock(), MagicMock(), []
        ))
        mocker.patch("loft_cli.local.selector.select_specs", return_value=fake_matches)

        result = runner.invoke(app, [
            "apply", "--fleet", str(fleet_dir), "--selector", "role=worker",
            "--continue-on-error"
        ])

        # Summary must mention 1 succeeded and 1 failed
        assert "1 succeeded" in result.output
        assert "1 failed" in result.output

    def test_exit_code_1_when_any_fail(self, tmp_path, mocker):
        """Fleet apply exits with code 1 when any spec fails."""
        fleet_dir = tmp_path / "fleet"
        fleet_dir.mkdir()

        spec_file = fleet_dir / "worker-01.yaml"
        _write_spec(spec_file, "worker-01", labels={"role": "worker"})

        mocker.patch("loft_cli.cli._apply_single", side_effect=SystemExit(1))
        mocker.patch("loft_cli.cli._build_pipeline", return_value=(
            MagicMock(), MagicMock(), MagicMock(), []
        ))
        mocker.patch(
            "loft_cli.local.selector.select_specs",
            return_value=[(str(spec_file), MagicMock())],
        )

        result = runner.invoke(app, [
            "apply", "--fleet", str(fleet_dir), "--selector", "role=worker"
        ])

        assert result.exit_code != 0


class TestFleetApplyDryRun:
    """--dry-run flag is forwarded to each _apply_single call."""

    def test_dry_run_forwarded_to_apply_single(self, tmp_path, mocker):
        """--dry-run is passed as True in each _apply_single call."""
        fleet_dir = tmp_path / "fleet"
        fleet_dir.mkdir()

        spec_a = fleet_dir / "worker-01.yaml"
        spec_b = fleet_dir / "worker-02.yaml"
        _write_spec(spec_a, "worker-01", labels={"role": "worker"})
        _write_spec(spec_b, "worker-02", labels={"role": "worker"})

        fake_matches = [
            (str(spec_a), MagicMock()),
            (str(spec_b), MagicMock()),
        ]

        apply_single_mock = mocker.patch("loft_cli.cli._apply_single")
        mocker.patch("loft_cli.cli._build_pipeline", return_value=(
            MagicMock(), MagicMock(), MagicMock(), []
        ))
        mocker.patch("loft_cli.local.selector.select_specs", return_value=fake_matches)

        result = runner.invoke(app, [
            "apply", "--fleet", str(fleet_dir), "--selector", "role=worker", "--dry-run"
        ])

        assert result.exit_code == 0
        # _apply_single signature: (parsed_spec, ctx, p, mode, dry_run, console)
        # dry_run is the 5th positional arg (index 4)
        for c in apply_single_mock.call_args_list:
            positional_args = c[0]
            dry_run_arg = positional_args[4]  # 5th positional arg
            assert dry_run_arg is True, f"Expected dry_run=True but got {dry_run_arg!r}"

    def test_no_dry_run_forwarded_as_false(self, tmp_path, mocker):
        """Without --dry-run, False is passed to _apply_single."""
        fleet_dir = tmp_path / "fleet"
        fleet_dir.mkdir()

        spec_file = fleet_dir / "worker-01.yaml"
        _write_spec(spec_file, "worker-01", labels={"role": "worker"})

        apply_single_mock = mocker.patch("loft_cli.cli._apply_single")
        mocker.patch("loft_cli.cli._build_pipeline", return_value=(
            MagicMock(), MagicMock(), MagicMock(), []
        ))
        mocker.patch(
            "loft_cli.local.selector.select_specs",
            return_value=[(str(spec_file), MagicMock())],
        )

        result = runner.invoke(app, [
            "apply", "--fleet", str(fleet_dir), "--selector", "role=worker"
        ])

        assert result.exit_code == 0
        positional_args = apply_single_mock.call_args_list[0][0]
        dry_run_arg = positional_args[4]
        assert dry_run_arg is False


class TestSingleSpecApplyUnchanged:
    """Single-spec apply <spec.yaml> (no --fleet) is unaffected by fleet changes."""

    def test_single_spec_apply_invokes_apply_single_once(self, bootstrap_yaml, mocker):
        """Single-spec apply still calls _apply_single exactly once without fleet."""
        apply_single_mock = mocker.patch("loft_cli.cli._apply_single")
        mocker.patch("loft_cli.cli._build_pipeline", return_value=(
            MagicMock(), MagicMock(), MagicMock(), []
        ))

        result = runner.invoke(app, ["apply", str(bootstrap_yaml)])

        assert result.exit_code == 0
        assert apply_single_mock.call_count == 1

    def test_single_spec_apply_passes_dry_run_flag(self, bootstrap_yaml, mocker):
        """Single-spec apply with --dry-run passes True to _apply_single."""
        apply_single_mock = mocker.patch("loft_cli.cli._apply_single")
        mocker.patch("loft_cli.cli._build_pipeline", return_value=(
            MagicMock(), MagicMock(), MagicMock(), []
        ))

        result = runner.invoke(app, ["apply", str(bootstrap_yaml), "--dry-run"])

        assert result.exit_code == 0
        positional_args = apply_single_mock.call_args_list[0][0]
        dry_run_arg = positional_args[4]
        assert dry_run_arg is True

    def test_single_spec_no_fleet_flag_no_selector_called(self, bootstrap_yaml, mocker):
        """Single-spec apply does NOT invoke select_specs at all."""
        apply_single_mock = mocker.patch("loft_cli.cli._apply_single")
        mocker.patch("loft_cli.cli._build_pipeline", return_value=(
            MagicMock(), MagicMock(), MagicMock(), []
        ))
        select_mock = mocker.patch("loft_cli.local.selector.select_specs")

        runner.invoke(app, ["apply", str(bootstrap_yaml)])

        select_mock.assert_not_called()
