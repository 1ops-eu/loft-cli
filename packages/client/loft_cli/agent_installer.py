"""Agent installation utilities.

Handles uploading and installing the loft-cli-agent binary on target servers,
and verifying agent availability.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from loft_cli_core.agent_paths import (
    AGENT_BINARY_PATH,
    AGENT_CONFIG_DIR,
    AGENT_LOG_DIR,
    AGENT_STATE_DIR,
)

if TYPE_CHECKING:
    from loft_cli.runtime.transport import Transport


def detect_agent(transport: Transport) -> str | None:
    """Check if loft-cli-agent is installed on the target and return its version.

    Returns the version string, or None if not installed.
    """
    result = transport.run(f"{AGENT_BINARY_PATH} version", sudo=False, warn=True)
    if result.ok and result.stdout.strip():
        # Output format: "loft-cli-agent X.Y.Z"
        parts = result.stdout.strip().split()
        return parts[-1] if parts else result.stdout.strip()
    return None


def check_version_compatibility(client_version: str, agent_version: str) -> tuple[bool, str]:
    """Check that client and agent major versions match.

    Returns (compatible: bool, message: str). A mismatch is an error from v1.0
    onwards — major versions must match for the plan format and API to be stable.
    """
    try:
        client_major = int(client_version.split(".")[0])
        agent_major = int(agent_version.split(".")[0])
    except (ValueError, IndexError):
        return True, ""  # Cannot parse — allow and let the apply fail naturally

    if client_major != agent_major:
        return False, (
            f"Client v{client_version} requires agent v{client_major}.x, "
            f"but agent v{agent_version} is installed. "
            f"Run: loft-cli agent-update <host>"
        )
    return True, ""


def install_agent_commands() -> list[str]:
    """Return the shell commands to create agent directories on the target.

    The actual binary upload is handled by the planner as an ssh_upload step.
    These commands are embedded in plan steps.
    """
    dirs = [str(AGENT_CONFIG_DIR), str(AGENT_STATE_DIR), str(AGENT_LOG_DIR)]
    return [f"mkdir -p {d}" for d in dirs]


def get_local_agent_binary() -> Path | None:
    """Locate the loft-cli-agent binary on the local system.

    Checks: 1) alongside the current loft-cli binary, 2) on PATH.
    Returns None if not found.
    """
    # Check alongside the running loft-cli binary
    import sys

    current = Path(sys.executable).parent / "loft-cli-agent"
    if current.exists():
        return current

    # Check PATH
    found = shutil.which("loft-cli-agent")
    if found:
        return Path(found)

    return None
