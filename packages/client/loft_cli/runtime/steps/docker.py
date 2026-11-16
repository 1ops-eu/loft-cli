"""Docker installation commands."""

from __future__ import annotations


def install_docker() -> str:
    """Install Docker only when it is missing. The installer script also upgrades an existing installation, and that
    restarts docker.service: every container on the host stops, a loft-cli applying from one of them included.
    """
    return "bash -c 'command -v docker >/dev/null 2>&1 || curl -fsSL https://get.docker.com | sh'"


def enable_docker() -> str:
    return "systemctl enable --now docker"


def docker_version_check() -> str:
    return "docker --version"
