"""Docker installation steps: installed only when missing, so a re-apply never restarts docker.service."""

from __future__ import annotations

from loft_cli.runtime.steps import docker as dk


def test_install_docker_runs_the_installer_only_when_docker_is_missing() -> None:
    cmd = dk.install_docker()
    assert cmd.startswith("bash -c 'command -v docker >/dev/null 2>&1 || ")
    assert "curl -fsSL https://get.docker.com | sh" in cmd
