"""Pydantic v2 models for kind: service YAML specs (RFC section 8)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from loft_cli_core.specs.bootstrap_schema import (
    CheckBlock,
    HostBlock,
    InventoryBlock,
    MetaBlock,
)


class ServiceLoginBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user: str = Field(
        default="admin",
        description="SSH username for connecting to the server (post-bootstrap admin account).",
    )
    private_key: str = Field(
        default="~/.ssh/id_ed25519", description="Path to the SSH private key for this connection."
    )
    password: str | None = Field(
        default=None, description="SSH password. Use only when key auth is not available."
    )
    port: int = Field(
        default=2222, description="SSH port on the server (post-bootstrap default is 2222)."
    )


class CreateRoleBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="PostgreSQL role name to create.")
    password_env: str = Field(
        default="", description="Environment variable name holding the password for this role."
    )


class CreateDatabaseBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="PostgreSQL database name to create.")
    owner: str = Field(default="", description="PostgreSQL role to set as the database owner.")


class PostgresBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(
        default=True, description="Set to true to install and configure PostgreSQL on this server."
    )
    version: str = Field(
        default="16", description="PostgreSQL major version to install, e.g. '16' or '15'."
    )
    listen_addresses: list[str] = Field(
        default_factory=lambda: ["127.0.0.1"],
        description="IP addresses PostgreSQL listens on. Use ['*'] to allow remote connections.",
    )
    create_role: CreateRoleBlock | None = Field(
        default=None, description="Optional PostgreSQL role to create during provisioning."
    )
    create_database: CreateDatabaseBlock | None = Field(
        default=None, description="Optional PostgreSQL database to create during provisioning."
    )


class NginxSiteBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain: str = Field(description="Domain name for this virtual host (e.g. 'example.com').")
    upstream: str = Field(
        default="", description="Upstream backend hostname or IP for reverse proxy."
    )
    upstream_port: int = Field(
        default=8080, description="Port on the upstream backend to proxy requests to."
    )
    listen_port: int = Field(default=80, description="Port Nginx listens on for this virtual host.")
    ssl: bool = Field(
        default=False, description="Set to true to enable SSL/TLS for this virtual host."
    )
    ssl_certificate: str = Field(
        default="", description="Path to the SSL certificate file on the server."
    )
    ssl_certificate_key: str = Field(
        default="", description="Path to the SSL certificate private key file on the server."
    )


class NginxBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(
        default=True, description="Set to true to install and configure Nginx on this server."
    )
    sites: list[NginxSiteBlock] = Field(
        default_factory=list, description="List of virtual host configurations to create."
    )


class DockerBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(
        default=True, description="Set to true to install Docker Engine on this server."
    )


class HealthCheckBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = Field(
        default="http", description="Health check type. Currently only 'http' is supported."
    )
    url: str = Field(default="", description="URL to poll for the HTTP health check.")
    expect_status: int = Field(
        default=200, description="Expected HTTP status code for a passing health check."
    )


class ContainerBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Docker container name.")
    image: str = Field(description="Docker image reference to run, e.g. 'nginx:alpine'.")
    ports: list[str] = Field(
        default_factory=list, description="Port mappings in Docker format, e.g. ['8080:80']."
    )
    env: dict[str, str] = Field(
        default_factory=dict, description="Environment variables to pass into the container."
    )
    env_file: str | None = Field(
        default=None,
        description="Path to a file of environment variables to pass into the container.",
    )
    restart: str = Field(
        default="unless-stopped",
        description="Docker restart policy: 'no', 'always', 'on-failure', or 'unless-stopped'.",
    )
    healthcheck: HealthCheckBlock | None = Field(
        default=None, description="Optional health check to verify the container is ready."
    )


class ServiceLocalBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state_dir: str = Field(
        default="", description="Override the local state directory. Defaults to ~/.loft-cli/."
    )
    inventory: InventoryBlock = Field(
        default_factory=InventoryBlock, description="Controls local inventory database recording."
    )


class ServiceSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["service"]
    meta: MetaBlock
    host: HostBlock
    login: ServiceLoginBlock = Field(default_factory=ServiceLoginBlock)
    postgres: PostgresBlock | None = None
    nginx: NginxBlock | None = None
    docker: DockerBlock | None = None
    containers: list[ContainerBlock] = Field(default_factory=list)
    local: ServiceLocalBlock = Field(default_factory=ServiceLocalBlock)
    checks: list[CheckBlock] = Field(default_factory=list)
