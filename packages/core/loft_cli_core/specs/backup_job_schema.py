"""Pydantic v2 models for kind: backup_job YAML specs.

Define host-local backup operations with retention semantics.
The planner generates a backup shell script and a systemd timer
to run it on schedule.
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


class BackupSource(BaseModel):
    """Source definition for backup operations."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["postgres_dump", "directory"] = Field(
        description="Backup source type: 'postgres_dump' for PostgreSQL databases, 'directory' for filesystem paths."
    )
    # postgres_dump fields
    database: str | None = Field(
        default=None,
        description="PostgreSQL database name to dump. Required when type is 'postgres_dump'.",
    )
    host: str = Field(
        default="localhost",
        description="PostgreSQL server hostname. Used when type is 'postgres_dump'.",
    )
    port: int = Field(
        default=5432, description="PostgreSQL port number. Used when type is 'postgres_dump'."
    )
    user: str = Field(
        default="postgres",
        description="PostgreSQL user for pg_dump. Used when type is 'postgres_dump'.",
    )
    docker_exec: str | None = Field(
        default=None, description="Docker container name to run pg_dump inside via 'docker exec'."
    )
    # directory fields
    path: str | None = Field(
        default=None, description="Filesystem path to back up. Required when type is 'directory'."
    )


class BackupDestination(BaseModel):
    """Destination for backup files."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(description="Local directory on the server where backup files are stored.")


class BackupRetention(BaseModel):
    """Retention policy for backups."""

    model_config = ConfigDict(extra="forbid")

    count: int = Field(
        default=7,
        description="Number of most recent backup files to keep. Older files are deleted automatically.",
    )


class BackupJobConfig(BaseModel):
    """Configuration for a backup job."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        description="Job name used for script and systemd timer naming, e.g. 'postgres-daily'."
    )
    source: BackupSource = Field(
        description="Source to back up: a PostgreSQL database or a filesystem directory."
    )
    destination: BackupDestination = Field(
        description="Destination directory where backup files are stored on the server."
    )
    retention: BackupRetention = Field(
        default_factory=BackupRetention,
        description="Retention policy controlling how many old backups to keep.",
    )
    schedule: str = Field(
        default="*-*-* 02:00:00",
        description="Systemd OnCalendar expression for backup scheduling, e.g. '*-*-* 02:00:00' for 2am daily.",
    )


class BackupJobLoginBlock(BaseModel):
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


class BackupJobLocalBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state_dir: str = Field(
        default="", description="Override the local state directory. Defaults to ~/.loft-cli/."
    )
    inventory: InventoryBlock = Field(
        default_factory=InventoryBlock, description="Controls local inventory database recording."
    )


class BackupJobSpec(BaseModel):
    """Spec for defining backup operations with retention and scheduling."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["backup_job"]
    meta: MetaBlock
    host: HostBlock
    login: BackupJobLoginBlock = Field(default_factory=BackupJobLoginBlock)
    backup: BackupJobConfig
    local: BackupJobLocalBlock = Field(default_factory=BackupJobLocalBlock)
    checks: list[CheckBlock] = Field(default_factory=list)
