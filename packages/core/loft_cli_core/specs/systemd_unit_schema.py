"""Pydantic v2 models for kind: systemd_unit YAML specs.

Deploy and manage host-native systemd services.  The planner generates
a complete .service unit file from structured declarations, writes it
to /etc/systemd/system/, and runs daemon-reload + enable + start.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from loft_cli_core.specs.bootstrap_schema import (
    CheckBlock,
    HostBlock,
    InventoryBlock,
    MetaBlock,
)


class SystemdUnitConfig(BaseModel):
    """Configuration for a systemd service unit."""

    model_config = ConfigDict(extra="forbid")

    unit_name: str = Field(
        description="Service unit name without the .service suffix, e.g. 'myapp'."
    )
    description: str = Field(
        default="",
        description="Human-readable description of the service, used in the unit file Description= field.",
    )
    exec_start: str = Field(description="Command to execute to start the service.")
    exec_stop: str | None = Field(
        default=None, description="Optional command to stop the service gracefully."
    )
    working_directory: str | None = Field(
        default=None, description="Working directory for the service process."
    )
    user: str = Field(default="root", description="OS user to run the service as.")
    group: str = Field(default="root", description="OS group to run the service as.")
    restart: str = Field(
        default="on-failure",
        description="Restart policy: 'no', 'always', 'on-failure', or 'on-abnormal'.",
    )
    restart_sec: int = Field(
        default=5, description="Seconds to wait before restarting the service after a failure."
    )
    after: list[str] = Field(
        default_factory=lambda: ["network.target"],
        description="Systemd units this service must start after.",
    )
    environment: dict[str, str] = Field(
        default_factory=dict, description="Environment variables to set for the service process."
    )
    environment_file: str | None = Field(
        default=None, description="Path to a file of environment variables to load for the service."
    )
    type: str = Field(
        default="simple",
        description="Systemd service type: 'simple', 'forking', 'oneshot', or 'notify'.",
    )
    wanted_by: str = Field(
        default="multi-user.target",
        description="Systemd target this service is wanted by (determines when it starts on boot).",
    )


class LogRotateConfig(BaseModel):
    """Optional logrotate configuration for the service."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(
        default=False,
        description="Set to true to create a logrotate configuration for this service.",
    )
    path: str = Field(
        default="", description="Log file path pattern to rotate, e.g. '/var/log/myapp/*.log'."
    )
    rotate: int = Field(default=7, description="Number of rotated log files to keep.")
    frequency: str = Field(
        default="daily", description="Rotation frequency: 'daily', 'weekly', or 'monthly'."
    )
    compress: bool = Field(
        default=True, description="Set to true to compress rotated log files with gzip."
    )
    max_size: str = Field(
        default="",
        description="Rotate when the log exceeds this size, e.g. '100M'. Empty disables size-based rotation.",
    )


class SystemdUnitLoginBlock(BaseModel):
    """Login defaults matching post-bootstrap convention (admin@2222)."""

    model_config = ConfigDict(extra="forbid")

    user: str = Field(default="admin", description="SSH username for connecting to the server.")
    private_key: str = Field(
        default="~/.ssh/id_ed25519", description="Path to the SSH private key for this connection."
    )
    password: str | None = Field(
        default=None, description="SSH password. Use only when key auth is not available."
    )
    port: int = Field(
        default=2222, description="SSH port on the server (post-bootstrap default is 2222)."
    )


class SystemdUnitLocalBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state_dir: str = Field(
        default="", description="Override the local state directory. Defaults to ~/.loft-cli/."
    )
    inventory: InventoryBlock = Field(
        default_factory=InventoryBlock, description="Controls local inventory database recording."
    )


class SystemdUnitSpec(BaseModel):
    """Spec for deploying and managing a host-native systemd service."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["systemd_unit"]
    meta: MetaBlock
    host: HostBlock
    login: SystemdUnitLoginBlock = Field(default_factory=SystemdUnitLoginBlock)
    unit: SystemdUnitConfig
    logrotate: LogRotateConfig | None = None
    local: SystemdUnitLocalBlock = Field(default_factory=SystemdUnitLocalBlock)
    checks: list[CheckBlock] = Field(default_factory=list)
