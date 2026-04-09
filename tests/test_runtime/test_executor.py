"""Tests for the plan executor — gate semantics, dependency skipping, dry run."""

from __future__ import annotations

from loft_cli.runtime.executor import Executor, StepResult
from loft_cli_core.plan.models import Plan, Step, StepKind, StepScope


def _make_plan(steps: list[Step]) -> Plan:
    for i, s in enumerate(steps):
        s.index = i
    return Plan(
        spec_name="test",
        spec_kind="bootstrap",
        target_host="1.2.3.4",
        spec_hash="abc",
        plan_hash="def",
        steps=steps,
        created_at="2026-01-01T00:00:00Z",
    )


def _step(
    id,
    kind=StepKind.SSH_COMMAND,
    scope=StepScope.REMOTE,
    gate=False,
    depends_on=None,
    command="echo ok",
) -> Step:
    return Step(
        id=id,
        index=0,
        description=id,
        scope=scope,
        kind=kind,
        command=command,
        gate=gate,
        depends_on=depends_on or [],
    )


def test_dry_run_all_steps_succeed(mock_ssh_session):
    steps = [
        _step("step_a"),
        _step("step_b"),
        _step("step_c"),
    ]
    p = _make_plan(steps)
    executor = Executor(plan=p, transport=mock_ssh_session)
    result = executor.apply(dry_run=True)

    assert result.status == "success"
    assert all(r.status == "success" for r in result.step_results)
    mock_ssh_session.run.assert_not_called()


def test_gate_failure_aborts_plan(mock_ssh_session, mocker):
    """When a REMOTE gate step fails, subsequent steps must be skipped and plan aborts."""
    mock_ssh_session.run.return_value = mocker.MagicMock(
        ok=False, stdout="", stderr="timeout", return_code=1
    )

    gate_step = _step("gate", kind=StepKind.GATE, gate=True, command="ssh_check:1.2.3.4:2222:admin")
    after_gate = _step("after_gate", depends_on=[0])

    p = _make_plan([gate_step, after_gate])

    # Mock the gate check to fail
    mocker.patch(
        "loft_cli.checks.ssh.check_ssh_reachable",
        return_value=mocker.MagicMock(passed=False, message="connection refused"),
    )

    executor = Executor(plan=p, transport=mock_ssh_session)
    result = executor.apply(dry_run=False)

    assert result.status == "failed"
    assert result.aborted_at == 0  # gate is step 0

    gate_result = next(r for r in result.step_results if r.step_id == "gate")
    assert gate_result.status == "failed"


def test_local_gate_failure_gives_warning_not_abort(mock_ssh_session, mocker):
    """When a LOCAL gate step fails, plan should not abort — status is success_with_local_warnings
    and steps that depend on the gate are skipped via depends_on."""
    # step 0: preflight (succeeds)
    preflight = _step("preflight", scope=StepScope.REMOTE, kind=StepKind.SSH_COMMAND)
    # step 1: WireGuard tunnel gate (LOCAL, fails)
    gate_step = _step(
        "wg_gate",
        kind=StepKind.GATE,
        scope=StepScope.LOCAL,
        gate=True,
        command="tunnel_ssh_gate:myhost:10.0.0.1:2222:deploy",
    )
    # step 2: delete_open_ssh_rule depends on the gate — should be skipped on gate failure
    dependent_step = _step("delete_open_ssh_rule", scope=StepScope.REMOTE, depends_on=[1])
    # step 3: local step with no dependency on gate — should still run
    local_step = _step("write_ssh_config", scope=StepScope.LOCAL, kind=StepKind.LOCAL_COMMAND)

    p = _make_plan([preflight, gate_step, dependent_step, local_step])

    # Mock tunnel_up to fail (simulates wg-quick not available / tunnel fails)
    mocker.patch(
        "loft_cli.local.tunnel.tunnel_up",
        return_value=(False, "wg-quick: command not found"),
    )
    mocker.patch("loft_cli.local.wireguard_store.save_wireguard_state")

    executor = Executor(plan=p, ssh_session=mock_ssh_session)
    result = executor.apply(dry_run=False)

    assert result.status == "success_with_local_warnings"
    assert result.aborted_at is None

    gate_result = next(r for r in result.step_results if r.step_id == "wg_gate")
    assert gate_result.status == "failed"

    dep_result = next(r for r in result.step_results if r.step_id == "delete_open_ssh_rule")
    assert dep_result.status == "skipped"


def test_dependency_failure_skips_dependent(mock_ssh_session, mocker):
    """If step A fails, step B with depends_on=[A] should be skipped."""
    from loft_cli.runtime.ssh import CommandResult

    # Step 0 succeeds (preflight), step 1 fails, step 2 depends on step 1 → skipped
    ok = CommandResult(ok=True, stdout="ok", stderr="", return_code=0)
    fail = CommandResult(ok=False, stdout="", stderr="err", return_code=1)
    mock_ssh_session.run.side_effect = [ok, fail]

    preflight = _step("preflight")  # index 0 — succeeds
    step_a = _step("step_a")  # index 1 — fails
    step_b = _step("step_b", depends_on=[1])  # depends on step_a (index 1)

    p = _make_plan([preflight, step_a, step_b])
    executor = Executor(plan=p, transport=mock_ssh_session)
    result = executor.apply(dry_run=False)

    result_b = next(r for r in result.step_results if r.step_id == "step_b")
    assert result_b.status == "skipped"


def test_tunnel_gate_skips_gracefully_when_wg_quick_missing(mock_ssh_session, mocker):
    """tunnel_ssh_gate: when wg-quick is not installed, gate returns success (not abort)."""
    # The tunnel gate should degrade gracefully when wireguard-tools are absent
    # on the local (test-runner) machine so that CI runs against real VMs still
    # complete even without a local wg-quick installation.
    mocker.patch(
        "loft_cli.local.tunnel.tunnel_up",
        return_value=(False, "wg-quick not found — install wireguard-tools"),
    )
    mocker.patch(
        "loft_cli.local.wireguard_store.save_wireguard_state",
    )

    gate_step = _step(
        "verify_ssh_over_wireguard_tunnel",
        kind=StepKind.GATE,
        scope=StepScope.LOCAL,
        gate=True,
        command="tunnel_ssh_gate:myhost:10.10.0.1:2222:admin",
    )
    after_gate = _step("delete_open_ssh_rule")

    p = _make_plan([gate_step, after_gate])
    executor = Executor(plan=p, ssh_session=mock_ssh_session)
    result = executor.apply(dry_run=False)

    gate_result = next(
        r for r in result.step_results if r.step_id == "verify_ssh_over_wireguard_tunnel"
    )
    assert (
        gate_result.status == "success"
    ), "Gate should succeed (not abort) when wg-quick is unavailable"
    assert "SKIPPED" in gate_result.output


def test_tunnel_gate_skips_gracefully_when_sudo_unavailable(mock_ssh_session, mocker):
    """tunnel_ssh_gate: sudo not available → gate skips gracefully (no abort)."""
    mocker.patch(
        "loft_cli.local.tunnel.tunnel_up",
        return_value=(False, "sudo access required for wg-quick"),
    )
    mocker.patch(
        "loft_cli.local.wireguard_store.save_wireguard_state",
    )

    gate_step = _step(
        "verify_ssh_over_wireguard_tunnel",
        kind=StepKind.GATE,
        scope=StepScope.LOCAL,
        gate=True,
        command="tunnel_ssh_gate:myhost:10.10.0.1:2222:admin",
    )

    p = _make_plan([gate_step])
    executor = Executor(plan=p, ssh_session=mock_ssh_session)
    result = executor.apply(dry_run=False)

    gate_result = result.step_results[0]
    assert gate_result.status == "success"
    assert result.aborted_at is None, "Plan should not be aborted when sudo is unavailable"


def test_tunnel_gate_fails_hard_when_tunnel_up_but_ssh_fails(mock_ssh_session, mocker):
    """tunnel_ssh_gate: wg-quick runs but SSH through tunnel fails → hard gate failure."""
    mocker.patch(
        "loft_cli.local.tunnel.tunnel_up",
        return_value=(True, "Tunnel wg-myhost is up"),
    )
    mocker.patch(
        "loft_cli.local.tunnel.tunnel_down",
        return_value=(True, "Tunnel wg-myhost is down"),
    )
    mocker.patch(
        "loft_cli.local.wireguard_store.save_wireguard_state",
    )
    mocker.patch(
        "loft_cli.checks.ssh.check_ssh_reachable",
        return_value=mocker.MagicMock(passed=False, message="connection refused"),
    )

    gate_step = _step(
        "verify_ssh_over_wireguard_tunnel",
        kind=StepKind.GATE,
        scope=StepScope.LOCAL,
        gate=True,
        command="tunnel_ssh_gate:myhost:10.10.0.1:2222:admin",
    )
    after_gate = _step("delete_open_ssh_rule")

    p = _make_plan([gate_step, after_gate])
    executor = Executor(plan=p, ssh_session=mock_ssh_session)
    result = executor.apply(dry_run=False)

    gate_result = next(
        r for r in result.step_results if r.step_id == "verify_ssh_over_wireguard_tunnel"
    )
    assert (
        gate_result.status == "failed"
    ), "Gate should hard-fail when tunnel is up but SSH through it fails"
    assert result.aborted_at == 0, "Plan should be aborted when tunnel SSH verification fails"


def test_local_step_failure_gives_warning_status(mock_ssh_session):
    """If a LOCAL step fails, status should be success_with_local_warnings (not failed)."""
    remote_step = _step("remote", scope=StepScope.REMOTE)
    local_step = _step(
        "local",
        scope=StepScope.LOCAL,
        kind=StepKind.LOCAL_COMMAND,
        command="fail_command",
    )

    p = _make_plan([remote_step, local_step])

    executor = Executor(plan=p, transport=mock_ssh_session)
    # Make local command raise an exception

    def fail_local(step):

        return StepResult(
            step_index=step.index,
            step_id=step.id,
            scope="local",
            status="failed",
            error="local fail",
        )

    executor._execute_local_command = fail_local
    result = executor.apply(dry_run=False)

    assert result.status == "success_with_local_warnings"


class TestTunnelSshGateUnavailable:
    """Tunnel gate skips gracefully when wg-quick tooling is unavailable."""

    def _make_tunnel_gate_plan(self):
        gate_step = _step(
            "verify_ssh_over_wireguard_tunnel",
            kind=StepKind.GATE,
            scope=StepScope.LOCAL,
            gate=False,
            command="tunnel_ssh_gate:myhost:10.10.0.1:2222:deploy",
        )
        return _make_plan([gate_step])

    def test_wg_quick_not_found_skips_gracefully(self, mock_ssh_session, mocker):
        """When wg-quick is not installed, the gate succeeds with a warning output."""
        mocker.patch(
            "loft_cli.local.tunnel.tunnel_up",
            return_value=(False, "wg-quick not found — install wireguard-tools"),
        )
        mocker.patch("loft_cli.local.wireguard_store.save_wireguard_state")

        p = self._make_tunnel_gate_plan()
        executor = Executor(plan=p, ssh_session=mock_ssh_session)
        result = executor.apply(dry_run=False)

        assert result.status == "success"
        gate_result = next(
            r for r in result.step_results if r.step_id == "verify_ssh_over_wireguard_tunnel"
        )
        assert gate_result.status == "success"
        assert "[SKIPPED]" in gate_result.output

    def test_sudo_denied_skips_gracefully(self, mock_ssh_session, mocker):
        """When sudo is denied for wg-quick, the gate succeeds with a warning output."""
        mocker.patch(
            "loft_cli.local.tunnel.tunnel_up",
            return_value=(False, "sudo access required for wg-quick"),
        )
        mocker.patch("loft_cli.local.wireguard_store.save_wireguard_state")

        p = self._make_tunnel_gate_plan()
        executor = Executor(plan=p, ssh_session=mock_ssh_session)
        result = executor.apply(dry_run=False)

        assert result.status == "success"
        gate_result = next(
            r for r in result.step_results if r.step_id == "verify_ssh_over_wireguard_tunnel"
        )
        assert gate_result.status == "success"
        assert "[SKIPPED]" in gate_result.output

    def test_timeout_skips_gracefully(self, mock_ssh_session, mocker):
        """When wg-quick times out, the gate succeeds with a warning output."""
        mocker.patch(
            "loft_cli.local.tunnel.tunnel_up",
            return_value=(False, "wg-quick up timed out (30s)"),
        )
        mocker.patch("loft_cli.local.wireguard_store.save_wireguard_state")

        p = self._make_tunnel_gate_plan()
        executor = Executor(plan=p, ssh_session=mock_ssh_session)
        result = executor.apply(dry_run=False)

        assert result.status == "success"
        gate_result = next(
            r for r in result.step_results if r.step_id == "verify_ssh_over_wireguard_tunnel"
        )
        assert gate_result.status == "success"
        assert "[SKIPPED]" in gate_result.output

    def test_actual_tunnel_failure_still_hard_fails(self, mock_ssh_session, mocker):
        """A genuine wg-quick failure (not tooling unavailable) still hard-aborts."""
        mocker.patch(
            "loft_cli.local.tunnel.tunnel_up",
            return_value=(
                False,
                "wg-quick up failed (exit 1): RTNETLINK answers: Operation not permitted",
            ),
        )
        mocker.patch("loft_cli.local.wireguard_store.save_wireguard_state")

        p = self._make_tunnel_gate_plan()
        executor = Executor(plan=p, ssh_session=mock_ssh_session)
        result = executor.apply(dry_run=False)

        assert result.status == "failed"
        gate_result = next(
            r for r in result.step_results if r.step_id == "verify_ssh_over_wireguard_tunnel"
        )
        assert gate_result.status == "failed"
