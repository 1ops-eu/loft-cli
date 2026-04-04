"""Tests for WireGuard tunnel safety gate in planner.

Validates that when WireGuard is enabled with registered_peers_only=true:
1. allow_ssh_on_wireguard — remote SSH command
2. verify_ssh_over_wireguard_tunnel — local GATE step
3. delete_open_ssh_rule — remote SSH command

The gate must come between allow and delete so that the open SSH rule
is preserved if tunnel verification fails.

When registered_peers_only=false (the default), only allow_ssh_on_wireguard
is emitted — no lockout risk means no gate and no open-rule deletion.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from loft_cli.compiler.normalizer import normalize
from loft_cli.compiler.planner import plan
from loft_cli_core.plan.models import StepKind, StepScope
from loft_cli_core.registry.local_paths import LocalPathsConfig, register_local_paths
from loft_cli_core.specs.loader import load_spec


def _make_wg_plan(tmp_path: Path, registered_peers_only: bool = True):
    """Create a plan from a WireGuard-enabled bootstrap spec.

    By default uses registered_peers_only=true so the tunnel gate is present.
    Pass registered_peers_only=False to test the no-gate path.
    """
    spec_yaml = textwrap.dedent(f"""\
        kind: bootstrap
        meta:
          name: wg-gate-test
          description: Test WireGuard tunnel safety gate
        host:
          name: wg-test-node
          address: 203.0.113.10
          os_family: debian
        login:
          user: root
          private_key: ~/.ssh/id_ed25519
          port: 22
        admin_user:
          name: deploy
          groups:
            - sudo
          pubkeys: []
        ssh:
          port: 2222
          disable_root_login: true
          disable_password_auth: true
        firewall:
          provider: ufw
          ssh_only: true
          registered_peers_only: {"true" if registered_peers_only else "false"}
        wireguard:
          enabled: true
          interface: wg0
          address: 10.10.0.1/24
          endpoint: 203.0.113.10:51820
          peer_address: 10.10.0.2/32
          persistent_keepalive: 25
        local:
          ssh_config:
            enabled: true
          inventory:
            enabled: false
        checks: []
    """)
    spec_file = tmp_path / "wg-bootstrap.yaml"
    spec_file.write_text(spec_yaml)

    register_local_paths(LocalPathsConfig(wg_state_base=tmp_path / "wg"))
    spec = load_spec(spec_file)
    ctx = normalize(spec, spec_dir=tmp_path)
    return plan(ctx)


def _make_nowg_plan(tmp_path: Path):
    """Create a plan from a non-WireGuard bootstrap spec."""
    spec_yaml = textwrap.dedent("""\
        kind: bootstrap
        meta:
          name: no-wg-test
          description: Test without WireGuard
        host:
          name: plain-node
          address: 192.168.1.100
          os_family: debian
        login:
          user: root
          private_key: ~/.ssh/id_ed25519
          port: 22
        admin_user:
          name: admin
          groups:
            - sudo
          pubkeys: []
        ssh:
          port: 2222
          disable_root_login: true
          disable_password_auth: false
        firewall:
          provider: ufw
          ssh_only: true
        wireguard:
          enabled: false
        local:
          ssh_config:
            enabled: true
          inventory:
            enabled: false
        checks: []
    """)
    spec_file = tmp_path / "no-wg-bootstrap.yaml"
    spec_file.write_text(spec_yaml)

    spec = load_spec(spec_file)
    ctx = normalize(spec, spec_dir=tmp_path)
    return plan(ctx)


class TestWireGuardTunnelGate:
    """Tests for the verify_ssh_over_wireguard_tunnel gate step.

    The gate is only emitted when registered_peers_only=true.
    """

    def test_gate_present_when_registered_peers_only(self, tmp_path):
        """Gate step must be present when registered_peers_only=true."""
        p = _make_wg_plan(tmp_path, registered_peers_only=True)
        gate_steps = [s for s in p.steps if s.id == "verify_ssh_over_wireguard_tunnel"]
        assert len(gate_steps) == 1, "Should have exactly one tunnel gate step"

    def test_gate_absent_when_not_registered_peers_only(self, tmp_path):
        """Gate step must NOT be present when registered_peers_only=false."""
        p = _make_wg_plan(tmp_path, registered_peers_only=False)
        gate_steps = [s for s in p.steps if s.id == "verify_ssh_over_wireguard_tunnel"]
        assert len(gate_steps) == 0, "Should have no tunnel gate when registered_peers_only=false"

    def test_delete_open_ssh_rule_absent_when_not_registered_peers_only(self, tmp_path):
        """delete_open_ssh_rule must NOT be present when registered_peers_only=false."""
        p = _make_wg_plan(tmp_path, registered_peers_only=False)
        delete_steps = [s for s in p.steps if s.id == "delete_open_ssh_rule"]
        assert (
            len(delete_steps) == 0
        ), "Should have no delete_open_ssh_rule when registered_peers_only=false"

    def test_allow_ssh_on_wireguard_present_when_wg_enabled(self, tmp_path):
        """allow_ssh_on_wireguard must always be present when WG is enabled."""
        p_peers = _make_wg_plan(tmp_path, registered_peers_only=True)
        p_any = _make_wg_plan(tmp_path, registered_peers_only=False)
        assert any(s.id == "allow_ssh_on_wireguard" for s in p_peers.steps)
        assert any(s.id == "allow_ssh_on_wireguard" for s in p_any.steps)

    def test_gate_absent_when_wg_disabled(self, tmp_path):
        p = _make_nowg_plan(tmp_path)
        gate_steps = [s for s in p.steps if s.id == "verify_ssh_over_wireguard_tunnel"]
        assert len(gate_steps) == 0, "Should have no tunnel gate when WG disabled"

    def test_gate_is_local_scope(self, tmp_path):
        p = _make_wg_plan(tmp_path)
        gate = next(s for s in p.steps if s.id == "verify_ssh_over_wireguard_tunnel")
        assert gate.scope == StepScope.LOCAL

    def test_gate_is_gate_kind(self, tmp_path):
        p = _make_wg_plan(tmp_path)
        gate = next(s for s in p.steps if s.id == "verify_ssh_over_wireguard_tunnel")
        assert gate.kind == StepKind.GATE
        assert gate.gate is True

    def test_gate_has_tunnel_ssh_gate_command(self, tmp_path):
        p = _make_wg_plan(tmp_path)
        gate = next(s for s in p.steps if s.id == "verify_ssh_over_wireguard_tunnel")
        assert gate.command.startswith("tunnel_ssh_gate:")

    def test_gate_command_contains_host_and_vpn_ip(self, tmp_path):
        p = _make_wg_plan(tmp_path)
        gate = next(s for s in p.steps if s.id == "verify_ssh_over_wireguard_tunnel")
        parts = gate.command.split(":")
        assert parts[0] == "tunnel_ssh_gate"
        assert parts[1] == "wg-test-node"  # host name
        assert parts[2] == "10.10.0.1"  # VPN IP (no CIDR)
        assert parts[3] == "2222"  # SSH port
        assert parts[4] == "deploy"  # admin user

    def test_gate_has_rollback_hint(self, tmp_path):
        p = _make_wg_plan(tmp_path)
        gate = next(s for s in p.steps if s.id == "verify_ssh_over_wireguard_tunnel")
        assert gate.rollback_hint
        assert "NOT deleted" in gate.rollback_hint

    def test_gate_has_wireguard_tags(self, tmp_path):
        p = _make_wg_plan(tmp_path)
        gate = next(s for s in p.steps if s.id == "verify_ssh_over_wireguard_tunnel")
        assert "wireguard" in gate.tags
        assert "gate" in gate.tags
        assert "tunnel" in gate.tags

    def test_three_wg_steps_in_order(self, tmp_path):
        """allow_ssh_on_wireguard < verify_ssh_over_wireguard_tunnel < delete_open_ssh_rule."""
        p = _make_wg_plan(tmp_path)

        allow = next(s for s in p.steps if s.id == "allow_ssh_on_wireguard")
        gate = next(s for s in p.steps if s.id == "verify_ssh_over_wireguard_tunnel")
        delete = next(s for s in p.steps if s.id == "delete_open_ssh_rule")

        assert allow.index < gate.index, (
            f"allow ({allow.index}) must come before gate ({gate.index})"
        )
        assert gate.index < delete.index, (
            f"gate ({gate.index}) must come before delete ({delete.index})"
        )

    def test_delete_open_ssh_rule_depends_on_wg_gate(self, tmp_path):
        """delete_open_ssh_rule must declare depends_on the WireGuard gate so it is
        skipped (not executed) when the gate fails, rather than requiring plan abort."""
        p = _make_wg_plan(tmp_path)
        gate = next(s for s in p.steps if s.id == "verify_ssh_over_wireguard_tunnel")
        delete = next(s for s in p.steps if s.id == "delete_open_ssh_rule")
        assert gate.index in delete.depends_on, (
            f"delete_open_ssh_rule.depends_on should include gate index {gate.index}, "
            f"got {delete.depends_on}"
        )

    def test_no_wg_steps_without_wireguard(self, tmp_path):
        p = _make_nowg_plan(tmp_path)
        wg_step_ids = {
            "allow_ssh_on_wireguard",
            "verify_ssh_over_wireguard_tunnel",
            "delete_open_ssh_rule",
        }
        for s in p.steps:
            assert s.id not in wg_step_ids, f"Step {s.id} should not exist without WireGuard"

    def test_plan_has_two_gates_with_registered_peers_only(self, tmp_path):
        """WG-enabled plan with registered_peers_only=true: admin login gate + tunnel gate = 2."""
        p = _make_wg_plan(tmp_path, registered_peers_only=True)
        gates = [s for s in p.steps if s.gate]
        assert len(gates) == 2
        gate_ids = {g.id for g in gates}
        assert "verify_admin_login_on_new_port" in gate_ids
        assert "verify_ssh_over_wireguard_tunnel" in gate_ids

    def test_plan_has_one_gate_without_registered_peers_only(self, tmp_path):
        """WG-enabled plan with registered_peers_only=false: only admin login gate = 1."""
        p = _make_wg_plan(tmp_path, registered_peers_only=False)
        gates = [s for s in p.steps if s.gate]
        assert len(gates) == 1
        assert gates[0].id == "verify_admin_login_on_new_port"

    def test_gate_description_contains_vpn_ip(self, tmp_path):
        p = _make_wg_plan(tmp_path)
        gate = next(s for s in p.steps if s.id == "verify_ssh_over_wireguard_tunnel")
        assert "10.10.0.1" in gate.description
        assert "2222" in gate.description
