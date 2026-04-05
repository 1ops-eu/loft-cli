"""Local SSH key management — ensure admin key pairs exist before applying."""

from __future__ import annotations

import subprocess
from pathlib import Path

from loft_cli_core.utils.files import expand_path


def ensure_ssh_keypair(provider: str, host: str, console=None) -> Path:
    """Generate SSH key pair at provider-scoped path.

    Creates ~/.loft-cli/keys/{provider}/{host}/id_ed25519

    Returns the path to the generated private key.
    """
    from loft_cli_core.registry.local_paths import ssh_key_dir

    key_dir = ssh_key_dir(provider, host)
    key_dir.mkdir(parents=True, exist_ok=True)

    priv_path = key_dir / "id_ed25519"
    pub_path = key_dir / "id_ed25519.pub"

    if priv_path.exists():
        priv_path.chmod(0o600)
        pub_path.chmod(0o644)
        if console:
            console.print(f"[dim]SSH keypair already exists: {priv_path}[/dim]")
        return priv_path

    try:
        subprocess.run(
            ["ssh-keygen", "-t", "ed25519", "-f", str(priv_path), "-N", ""],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Failed to generate SSH key pair at {priv_path}: {e.stderr.decode().strip()}"
        ) from e

    priv_path.chmod(0o600)
    pub_path.chmod(0o644)

    if console:
        console.print(f"[green]✓ Generated SSH key pair:[/green] {priv_path}")

    return priv_path


def ensure_admin_keys(spec, console=None) -> None:
    """Generate SSH key pairs for any admin pubkeys whose private key is absent.

    Only runs when the auth method is key-based (pubkeys list is non-empty).
    Skips any pubkey path that doesn't follow the conventional '<name>.pub'
    pattern, since we can't safely derive the private key path from it.

    Root's login key is assumed to exist when private_key auth is used — we
    never auto-generate it here.

    When pubkeys is empty or contains "auto", uses provider-scoped path.
    """
    provider = getattr(spec.host, "provider", "") or ""
    host = spec.host.name

    auto_keys = not spec.admin_user.pubkeys or "auto" in spec.admin_user.pubkeys
    if auto_keys and provider:
        ensure_ssh_keypair(provider, host, console=console)
        return

    for pubkey_path_str in spec.admin_user.pubkeys:
        if pubkey_path_str == "auto":
            continue

        pub_path = expand_path(pubkey_path_str)

        if pub_path.suffix != ".pub":
            continue

        priv_path = pub_path.with_suffix("")

        if priv_path.exists():
            continue

        pub_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(
                ["ssh-keygen", "-t", "ed25519", "-f", str(priv_path), "-N", ""],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Failed to generate SSH key pair at {priv_path}: {e.stderr.decode().strip()}"
            ) from e

        if console:
            console.print(f"[green]✓ Generated SSH key pair:[/green] {priv_path}")
