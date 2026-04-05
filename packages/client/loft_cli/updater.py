"""Self-update and agent-update utilities.

Checks GitHub Releases for new versions and handles binary replacement.
"""

from __future__ import annotations

import platform
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import requests
from rich.console import Console

if TYPE_CHECKING:
    from loft_cli.runtime.transport import Transport

GITHUB_REPO = "1ops-eu/loft-cli"
RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def get_latest_release() -> dict:
    """Query GitHub API for the latest release.

    Returns a dict with 'tag_name', 'assets' list, etc.
    Raises on network/API errors.
    """
    resp = requests.get(RELEASES_API, timeout=10)
    resp.raise_for_status()
    return resp.json()


def parse_version(tag: str) -> tuple[int, ...]:
    """Parse a version tag like 'v0.4.0' into a comparable tuple."""
    clean = tag.lstrip("v")
    return tuple(int(p) for p in clean.split(".") if p.isdigit())


def is_newer(current: str, latest_tag: str) -> bool:
    """Return True if latest_tag is newer than current version."""
    return parse_version(latest_tag) > parse_version(current)


def _platform_suffix() -> str:
    """Determine the binary suffix for the current platform."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    arch_map = {"x86_64": "amd64", "amd64": "amd64", "aarch64": "arm64", "arm64": "arm64"}
    arch = arch_map.get(machine, machine)

    if system == "darwin":
        return f"macos-{arch}"
    return f"{system}-{arch}"


def find_asset_url(release: dict, suffix: str) -> str | None:
    """Find the download URL for a binary matching the given platform suffix."""
    for asset in release.get("assets", []):
        name = asset.get("name", "")
        if suffix in name and not name.endswith(".sha256"):
            return asset.get("browser_download_url")
    return None


def self_update(console: Console | None = None) -> bool:
    """Check for updates and replace the current binary if newer.

    Returns True if an update was applied.
    """
    from loft_cli import __version__

    c = console or Console()

    c.print(f"[dim]Current version: {__version__}[/dim]")
    c.print("[dim]Checking for updates...[/dim]")

    try:
        release = get_latest_release()
    except Exception as e:
        c.print(f"[red]Failed to check for updates: {e}[/red]")
        return False

    latest_tag = release.get("tag_name", "")
    if not is_newer(__version__, latest_tag):
        c.print(f"[green]Already up to date ({__version__})[/green]")
        return False

    c.print(f"[bold]New version available: {latest_tag}[/bold]")

    suffix = _platform_suffix()
    url = find_asset_url(release, suffix)
    if not url:
        c.print(
            f"[yellow]No binary found for platform '{suffix}'. "
            f"Try: pip install --upgrade loft-cli[/yellow]"
        )
        return False

    c.print(f"[dim]Downloading {url}...[/dim]")
    try:
        resp = requests.get(url, stream=True, timeout=60)
        resp.raise_for_status()

        current_binary = Path(sys.executable)
        if current_binary.name == "python" or current_binary.name.startswith("python"):
            c.print(
                "[yellow]Running from Python interpreter — "
                "use pip install --upgrade loft-cli instead[/yellow]"
            )
            return False

        # Download to temp file, then replace
        tmp_path = current_binary.with_suffix(".tmp")
        with open(tmp_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        # Make executable and replace
        tmp_path.chmod(0o755)
        tmp_path.rename(current_binary)

        c.print(f"[bold green]Updated to {latest_tag}[/bold green]")
        return True

    except Exception as e:
        c.print(f"[red]Update failed: {e}[/red]")
        return False


def update_agent(transport: Transport, console: Console | None = None) -> bool:
    """Update the loft-cli-agent binary on a remote host.

    Tries to download the agent binary from GitHub Releases first.
    Falls back to uploading the locally-available loft-cli-agent binary
    (e.g. when running in CI without a published release, or when the
    local binary is already up to date with the latest release).

    Returns True if an update was applied.
    """
    from loft_cli.agent_installer import detect_agent, get_local_agent_binary
    from loft_cli_core.agent_paths import AGENT_BINARY_PATH

    c = console or Console()

    # Check current agent version
    current = detect_agent(transport)
    c.print(f"[dim]Agent version: {current or 'not installed'}[/dim]")

    # Try GitHub Releases first
    release = None
    latest_tag = ""
    try:
        release = get_latest_release()
        latest_tag = release.get("tag_name", "")
    except Exception as e:
        c.print(f"[yellow]Could not check GitHub for updates: {e}[/yellow]")

    if release and current and not is_newer(current, latest_tag):
        c.print(f"[green]Agent already up to date ({current})[/green]")
        return False

    # Attempt to download the release binary from GitHub
    remote_binary_content: bytes | None = None
    if release and latest_tag:
        c.print(f"[bold]Updating agent to {latest_tag}[/bold]")

        # Detect target architecture
        arch_result = transport.run("uname -m", warn=True)
        machine = arch_result.stdout.strip() if arch_result.ok else "x86_64"
        arch_map = {"x86_64": "amd64", "aarch64": "arm64"}
        arch = arch_map.get(machine, machine)
        suffix = f"linux-{arch}"

        url = find_asset_url(release, f"agent-{suffix}")
        if url:
            c.print(f"[dim]Downloading {url}...[/dim]")
            try:
                resp = requests.get(url, stream=True, timeout=60)
                resp.raise_for_status()
                remote_binary_content = resp.content
            except Exception as e:
                c.print(f"[yellow]Download from GitHub failed: {e}[/yellow]")
        else:
            c.print(
                f"[yellow]No agent binary found for {suffix} in release {latest_tag}. "
                f"Trying local binary fallback.[/yellow]"
            )

    if remote_binary_content is not None:
        # Upload the downloaded binary via transport
        import os
        import tempfile

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
                f.write(remote_binary_content)
                tmp_local = f.name

            transport.upload(tmp_local, "/tmp/loft-cli-agent.tmp")
            transport.run(f"mv /tmp/loft-cli-agent.tmp {AGENT_BINARY_PATH}", sudo=True, warn=True)
            transport.run(f"chmod 755 {AGENT_BINARY_PATH}", sudo=True, warn=True)

            os.unlink(tmp_local)

            new_version = detect_agent(transport)
            if not new_version:
                c.print(
                    "[red]Agent binary was uploaded but verification failed — "
                    "the installed binary did not respond correctly.[/red]"
                )
                return False
            c.print(f"[bold green]Agent updated to {new_version}[/bold green]")
            return True

        except Exception as e:
            c.print(f"[yellow]GitHub binary upload failed: {e}. Trying local fallback.[/yellow]")

    # Fall back to the locally-available loft-cli-agent binary
    local_binary = get_local_agent_binary()
    if local_binary is None:
        c.print(
            "[red]No agent binary available: GitHub release download failed and "
            "loft-cli-agent is not installed locally. "
            "Install loft-cli-agent: pip install loft-cli-agent[/red]"
        )
        return False

    c.print(f"[dim]Using local binary: {local_binary}[/dim]")
    try:
        transport.upload(str(local_binary), "/tmp/loft-cli-agent.tmp")
        transport.run(f"mv /tmp/loft-cli-agent.tmp {AGENT_BINARY_PATH}", sudo=True, warn=True)
        transport.run(f"chmod 755 {AGENT_BINARY_PATH}", sudo=True, warn=True)

        new_version = detect_agent(transport)
        if not new_version:
            c.print(
                "[red]Local agent binary was uploaded but verification failed — "
                "the installed binary did not respond correctly.[/red]"
            )
            return False
        c.print(f"[bold green]Agent installed from local binary ({new_version})[/bold green]")
        return True

    except Exception as e:
        c.print(f"[red]Agent update failed: {e}[/red]")
        return False
