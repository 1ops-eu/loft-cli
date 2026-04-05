"""Local WireGuard state storage.

After a successful WireGuard bootstrap, loft-cli persists a local copy of
all key material and configuration under:

    {wg_state_base}/{host_name}/
        private.key   — server Curve25519 private key (mode 0600)
        public.key    — server public key derived via PyNaCl (mode 0644)
        wg0.conf      — server wg-quick config deployed to remote (mode 0600)
        client.key    — auto-generated client private key (mode 0600)
        client.conf   — client wg-quick config for local use (mode 0600)
        metadata.json — interface details, peer config, deployment provenance

When ``host.provider`` is set (e.g. ``"hetzner"``), state is stored under a
provider-scoped subdirectory instead:

    {wg_state_base}/{provider}/{host_name}/

This prevents collisions when the same host name is used across different
cloud providers.  The metadata.json file records the provider so that tools
like ``loft-cli tunnel up`` can locate the state by host name alone.

The base directory is addon-overridable via ``register_local_paths()``, so
commercial clones can use a deeper nested structure without touching this file:

    register_local_paths(LocalPathsConfig(
        wg_state_base=Path("~/.wg/mycompany/project1/").expanduser(),
    ))
    # → ~/.wg/mycompany/project1/{provider}/{host_name}/private.key  etc.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from loft_cli_core.utils.files import ensure_dir


def _wg_host_dir(host_name: str, provider: str = "") -> Path:
    """Return the per-host WireGuard state directory (not yet created).

    When *provider* is non-empty the directory is namespaced under the provider:
    ``{wg_state_base}/{provider}/{host_name}``.  Otherwise the legacy flat
    layout ``{wg_state_base}/{host_name}`` is used.
    """
    from loft_cli_core.registry.local_paths import get_local_paths, provider_wg_state_base

    wg_base = provider_wg_state_base(provider, get_local_paths())
    return wg_base / host_name


def find_wg_host_dir(host_name: str) -> Path | None:
    """Locate the per-host WireGuard state directory by host name.

    Searches in order:
    1. Flat layout: ``{wg_state_base}/{host_name}/``
    2. Provider-scoped: ``{wg_state_base}/{provider}/{host_name}/`` for any
       subdirectory of ``wg_state_base`` that contains a ``{host_name}/``
       sub-subdirectory.

    Returns the first matching directory that exists, or ``None``.
    """
    from loft_cli_core.registry.local_paths import get_local_paths

    base = get_local_paths().wg_state_base

    # 1. Flat (no provider)
    flat = base / host_name
    if flat.is_dir():
        return flat

    # 2. Provider-scoped — scan one level deep
    if base.exists():
        for sub in sorted(base.iterdir()):
            if sub.is_dir():
                candidate = sub / host_name
                if candidate.is_dir():
                    return candidate

    return None


def save_wireguard_state(
    *,
    host_name: str,
    provider: str | None = None,
    spec_name: str,
    private_key: str,
    public_key: str,
    wg_conf_content: str,
    client_private_key: str,
    client_public_key: str,
    client_conf_content: str,
    interface: str,
    address: str,
    endpoint: str,
    peer_address: str,
    persistent_keepalive: int,
) -> Path:
    """Persist WireGuard key material and config for one host.

    Parameters
    ----------
    host_name:
        Value of ``spec.host.name`` — used as the directory name.
    spec_name:
        Value of ``spec.meta.name`` — recorded in metadata for provenance.
    private_key:
        Base64-encoded Curve25519 server private key (contents of private_key_file).
    public_key:
        Derived server public key (populated by the normalizer via PyNaCl).
    wg_conf_content:
        Exact string uploaded to ``/etc/wireguard/{interface}.conf`` on the remote.
    client_private_key:
        Auto-generated client Curve25519 private key (base64).
    client_public_key:
        Derived client public key.
    client_conf_content:
        Client wg-quick config for local use (``wg-quick up client.conf``).
    interface:
        WireGuard interface name (e.g. ``wg0``).
    address:
        Server interface CIDR address (e.g. ``10.10.0.1/24``).
    endpoint:
        Server public endpoint (e.g. ``192.168.56.10:51820``).
    peer_address:
        Client/peer VPN IP CIDR (e.g. ``10.10.0.2/32``).
    persistent_keepalive:
        Keepalive interval in seconds.
    provider:
        Optional cloud/VPS provider name (e.g. ``"hetzner"``).  When non-empty,
        state is stored under ``{wg_state_base}/{provider}/{host_name}/``.

    Returns
    -------
    Path
        The per-host directory that was created/updated.
    """
    host_dir = _wg_host_dir(host_name, provider)
    ensure_dir(host_dir, mode=0o700)

    # Server private key — write-once (stable server identity across re-runs)
    server_key_path = host_dir / "private.key"
    if not server_key_path.exists():
        _write(server_key_path, private_key + "\n", mode=0o600)

    # Server public key — not secret
    _write(host_dir / "public.key", public_key + "\n", mode=0o644)

    # Server wg-quick config deployed to remote — contains private key
    _write(host_dir / f"{interface}.conf", wg_conf_content, mode=0o600)

    # Client private key — only write if not already present (stable peer identity)
    client_key_path = host_dir / "client.key"
    if not client_key_path.exists():
        _write(client_key_path, client_private_key + "\n", mode=0o600)

    # Client wg-quick config for local use — always refresh (server config may change)
    _write(host_dir / "client.conf", client_conf_content, mode=0o600)

    # metadata — provenance + interface/peer summary
    metadata = {
        "host_name": host_name,
        "provider": provider,
        "spec_name": spec_name,
        "deployed_at": datetime.now(UTC).isoformat(),
        "interface": interface,
        "client_interface": f"wg-{provider + '--' if provider else ''}{host_name}"[:15],
        "address": address,
        "endpoint": endpoint,
        "peer_address": peer_address,
        "persistent_keepalive": persistent_keepalive,
        "server_public_key": public_key,
        "client_public_key": client_public_key,
    }
    _write(
        host_dir / "metadata.json",
        json.dumps(metadata, indent=2) + "\n",
        mode=0o644,
    )

    return host_dir


def persist_wireguard_keys(
    *,
    host_name: str,
    private_key: str,
    client_private_key: str,
) -> None:
    """Eagerly persist auto-generated WireGuard key material to disk.

    Called by the normalizer immediately after generating fresh keys so that the
    server and client identities survive even if the subsequent ``apply`` is
    aborted before ``save_wireguard_state`` is reached (e.g. the tunnel-safety
    gate fails and the LOCAL ``save_local_wireguard_state`` step is skipped).

    Uses write-once semantics identical to ``save_wireguard_state``:

    * If the file already exists it is **not** overwritten — callers that
      loaded an existing key from disk will therefore never change it.
    * The parent directory is created with mode ``0o700`` if absent.

    Parameters
    ----------
    host_name:
        Value of ``spec.host.name`` — used as the directory name.
    private_key:
        Base64-encoded Curve25519 server private key.
    client_private_key:
        Base64-encoded Curve25519 client private key.
    """
    host_dir = _wg_host_dir(host_name)
    ensure_dir(host_dir, mode=0o700)

    server_key_path = host_dir / "private.key"
    if not server_key_path.exists():
        _write(server_key_path, private_key + "\n", mode=0o600)

    client_key_path = host_dir / "client.key"
    if not client_key_path.exists():
        _write(client_key_path, client_private_key + "\n", mode=0o600)


def _write(path: Path, content: str, mode: int) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(mode)
