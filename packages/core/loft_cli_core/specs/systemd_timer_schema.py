"""Pydantic v2 models for kind: systemd_timer YAML specs.

Deploy scheduled execution via systemd timers.  The planner generates
both a .timer and a companion .service (Type=oneshot) unit file, writes
them to /etc/systemd/system/, and runs daemon-reload + enable --now.
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


class TimerConfig(BaseModel):
    """Configuration for the systemd timer unit."""

    model_config = ConfigDict(extra="forbid")

    timer_name: str = Field(
        description="Timer unit name without the .timer suffix, e.g. 'backup-db'."
    )
    description: str = Field(
        default="", description="Human-readable description used in the .timer unit file."
    )
    on_calendar: str = Field(
        description="Systemd OnCalendar expression for scheduling, e.g. '*-*-* 02:00:00'."
    )
    persistent: bool = Field(
        default=True, description="Set to true to run missed timer events on the next boot."
    )
    accuracy_sec: str = Field(
        default="1min", description="Systemd AccuracySec value; controls scheduling precision."
    )


class TimerServiceConfig(BaseModel):
    """Configuration for the oneshot service triggered by the timer."""

    model_config = ConfigDict(extra="forbid")

    exec_start: str = Field(description="Command to execute when the timer fires.")
    user: str = Field(default="root", description="OS user to run the timer service as.")
    group: str = Field(default="root", description="OS group to run the timer service as.")
    working_directory: str | None = Field(
        default=None, description="Working directory for the timer service process."
    )
    environment: dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables to set for the timer service process.",
    )


class SystemdTimerLoginBlock(BaseModel):
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


class SystemdTimerLocalBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state_dir: str = Field(
        default="", description="Override the local state directory. Defaults to ~/.loft-cli/."
    )
    inventory: InventoryBlock = Field(
        default_factory=InventoryBlock, description="Controls local inventory database recording."
    )


class SystemdTimerSpec(BaseModel):
    """Spec for deploying scheduled execution via systemd timers."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["systemd_timer"]
    meta: MetaBlock
    host: HostBlock
    login: SystemdTimerLoginBlock = Field(default_factory=SystemdTimerLoginBlock)
    timer: TimerConfig
    service: TimerServiceConfig
    local: SystemdTimerLocalBlock = Field(default_factory=SystemdTimerLocalBlock)
    checks: list[CheckBlock] = Field(default_factory=list)
