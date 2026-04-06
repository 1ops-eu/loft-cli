"""Pydantic v2 models for kind: postgres_ensure YAML specs.

Ensure PostgreSQL resources exist on a running instance (container via
docker exec or host/port).  Structured declarations only: users,
databases, extensions, grants.  Every action appears as a discrete,
reviewable plan step.  No arbitrary SQL passthrough.
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


class PgConnection(BaseModel):
    """Connection parameters for the PostgreSQL instance."""

    model_config = ConfigDict(extra="forbid")

    host: str = Field(default="localhost", description="Hostname or IP of the PostgreSQL server.")
    port: int = Field(default=5432, description="PostgreSQL port number.")
    admin_user: str = Field(
        default="postgres",
        description="PostgreSQL superuser account used to create roles and databases.",
    )
    docker_exec: str | None = Field(
        default=None,
        description="Docker container name to run psql inside via 'docker exec'. Overrides host/port when set.",
    )


class PgUser(BaseModel):
    """A PostgreSQL user/role to ensure exists."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="PostgreSQL role/user name to ensure exists.")
    password_env: str | None = Field(
        default=None,
        description="Environment variable name holding the password for this role. Resolved at plan time.",
    )


class PgDatabase(BaseModel):
    """A PostgreSQL database to ensure exists."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="PostgreSQL database name to ensure exists.")
    owner: str = Field(
        default="postgres", description="PostgreSQL role to set as the database owner."
    )


class PgExtension(BaseModel):
    """A PostgreSQL extension to ensure is installed."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        description="PostgreSQL extension name to install, e.g. 'pgcrypto' or 'uuid-ossp'."
    )
    database: str = Field(description="Database to install the extension in.")


class PgGrant(BaseModel):
    """A PostgreSQL privilege grant."""

    model_config = ConfigDict(extra="forbid")

    privilege: str = Field(
        description="Privilege to grant: ALL, SELECT, INSERT, UPDATE, DELETE, etc."
    )
    on_database: str = Field(description="Database to grant the privilege on.")
    to_user: str = Field(description="PostgreSQL role to grant the privilege to.")


class PostgresEnsureLoginBlock(BaseModel):
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


class PostgresEnsureLocalBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state_dir: str = Field(
        default="", description="Override the local state directory. Defaults to ~/.loft-cli/."
    )
    inventory: InventoryBlock = Field(
        default_factory=InventoryBlock, description="Controls local inventory database recording."
    )


class PostgresEnsureSpec(BaseModel):
    """Spec for ensuring PostgreSQL resources exist on a running instance."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["postgres_ensure"]
    meta: MetaBlock
    host: HostBlock
    login: PostgresEnsureLoginBlock = Field(default_factory=PostgresEnsureLoginBlock)
    connection: PgConnection = Field(default_factory=PgConnection)
    users: list[PgUser] = Field(default_factory=list)
    databases: list[PgDatabase] = Field(default_factory=list)
    extensions: list[PgExtension] = Field(default_factory=list)
    grants: list[PgGrant] = Field(default_factory=list)
    local: PostgresEnsureLocalBlock = Field(default_factory=PostgresEnsureLocalBlock)
    checks: list[CheckBlock] = Field(default_factory=list)
