"""Pydantic v2 models for kind: bootstrap YAML specs (RFC section 7)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MetaBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        description="Human-readable name for this spec, used as the inventory key and in log output."
    )
    description: str = Field(
        default="", description="Optional longer description of this spec's purpose."
    )
    labels: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Arbitrary key=value labels for fleet selection. "
            "Used by 'loft-cli fleet' commands to target subsets of specs, "
            "e.g. role=worker, env=staging."
        ),
    )


class HostBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        description="Human-readable name for this host, used as the SSH alias and inventory key."
    )
    address: str = Field(description="Public IP address or DNS hostname of the target server.")
    os_family: str = Field(
        default="debian",
        description="OS family on the target server. Currently only 'debian' (Debian/Ubuntu) is supported.",
    )
    provider: str = Field(
        default="",
        description="Cloud provider name (e.g. 'hetzner', 'ionos', 'generic'). Used for SSH key scoping.",
    )


class LoginBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user: str = Field(
        default="root",
        description="SSH username used for the initial login before bootstrap completes.",
    )
    private_key: str = Field(
        default="~/.ssh/id_ed25519",
        description="Path to the SSH private key used for initial login.",
    )
    password: str | None = Field(
        default=None,
        description="SSH password for initial login. Use only when key auth is not available.",
    )
    port: int = Field(
        default=22, description="SSH port for initial login (before bootstrap changes it)."
    )


class AdminUserBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        default="admin",
        description="Username for the non-root admin account created during bootstrap.",
    )
    groups: list[str] = Field(
        default_factory=lambda: ["sudo"],
        description="Supplementary groups for the admin user. Must include 'sudo' for privilege escalation.",
    )
    pubkeys: list[str] = Field(
        default_factory=list,
        description="List of SSH public keys to install in the admin user's authorized_keys file.",
    )


class SSHBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    port: int = Field(
        default=2222,
        description="SSH port to configure on the server after bootstrap. Should differ from 22 for security.",
    )
    disable_root_login: bool = Field(
        default=True, description="Set to true to disable direct root SSH login (recommended)."
    )
    disable_password_auth: bool = Field(
        default=False,
        description="Set to true to disable SSH password authentication and require key-based auth only.",
    )


class AllowPortRule(BaseModel):
    """An additional firewall rule to allow inbound traffic on a given port."""

    model_config = ConfigDict(extra="forbid")

    port: int = Field(description="TCP/UDP port number to allow inbound traffic on.")
    proto: str = Field(default="tcp", description="Protocol to allow: 'tcp', 'udp', or 'any'.")
    comment: str = Field(default="", description="Optional comment for the UFW firewall rule.")


class FirewallBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = Field(
        default="ufw",
        description="Firewall provider to configure. Currently only 'ufw' is supported.",
    )
    ssh_only: bool = Field(
        default=True,
        description="Set to true to allow only SSH traffic by default (all other inbound blocked).",
    )
    registered_peers_only: bool = Field(
        default=False,
        description="When wireguard is enabled, restrict SSH to declared WireGuard peer IPs only.",
    )
    allow_ports: list[AllowPortRule] = Field(
        default_factory=list,
        description="Additional inbound port rules to add beyond the SSH default.",
    )


class WireGuardBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(
        default=False, description="Set to true to configure WireGuard VPN on this host."
    )
    interface: str = Field(
        default="wg0", description="WireGuard network interface name to create on the server."
    )
    address: str = Field(
        default="", description="Server VPN interface CIDR address, e.g. '10.10.0.1/24'."
    )
    private_key_file: str = Field(
        default="", description="Path to the server's Curve25519 WireGuard private key file."
    )
    endpoint: str = Field(
        default="", description="Server's public WireGuard endpoint, e.g. '192.168.56.10:51820'."
    )
    peer_address: str = Field(
        default="", description="Client/peer VPN IP CIDR, e.g. '10.10.0.2/32'."
    )
    persistent_keepalive: int = Field(
        default=25, description="WireGuard PersistentKeepalive interval in seconds."
    )


class SSHConfigBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(
        default=True,
        description="Set to true to write a Host entry in the local SSH config file after bootstrap.",
    )
    host_alias: str = Field(
        default="",
        description="SSH Host alias to use in ~/.ssh/config. Defaults to '{provider}--{host.name}' when empty.",
    )
    config_path: str = Field(
        default="~/.ssh/config", description="Path to the local SSH config file to update."
    )
    preserve_legacy_entry: bool = Field(
        default=False,
        description="Set to true to keep any pre-existing Host entry in the main SSH config.",
    )


class InventoryBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(
        default=True,
        description="Set to true to record this host in the local encrypted inventory database.",
    )
    db_path: str = Field(
        default="~/.loft-cli/inventory.db",
        description="Path to the local SQLite inventory database file.",
    )


class LocalBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state_dir: str = Field(
        default="",
        description="Override the local state directory (SSH keys, inventory DB). Defaults to ~/.loft-cli/.",
    )
    ssh_config: SSHConfigBlock = Field(
        default_factory=SSHConfigBlock,
        description="Controls whether and how the local SSH config file is updated.",
    )
    inventory: InventoryBlock = Field(
        default_factory=InventoryBlock, description="Controls local inventory database recording."
    )


class CheckBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = Field(
        description="Check type: 'port_open', 'user_exists', 'interface_up', 'container_running', or 'http'."
    )
    port: int | None = Field(default=None, description="Port number for 'port_open' checks.")
    user: str | None = Field(default=None, description="Username for 'user_exists' checks.")
    interface: str | None = Field(
        default=None, description="Network interface name for 'interface_up' checks."
    )
    host: str | None = Field(
        default=None, description="Host to connect to for port checks (defaults to localhost)."
    )
    name: str | None = Field(
        default=None, description="Container name for 'container_running' checks."
    )
    url: str | None = Field(default=None, description="URL for 'http' checks.")
    expect_status: int | None = Field(
        default=None, description="Expected HTTP status code for 'http' checks."
    )


class BootstrapSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["bootstrap"]
    meta: MetaBlock
    host: HostBlock
    login: LoginBlock = Field(default_factory=LoginBlock)
    admin_user: AdminUserBlock = Field(default_factory=AdminUserBlock)
    ssh: SSHBlock = Field(default_factory=SSHBlock)
    firewall: FirewallBlock = Field(default_factory=FirewallBlock)
    wireguard: WireGuardBlock = Field(default_factory=WireGuardBlock)
    local: LocalBlock = Field(default_factory=LocalBlock)
    checks: list[CheckBlock] = Field(default_factory=list)
