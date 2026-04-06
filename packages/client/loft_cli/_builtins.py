"""Register the built-in core spec kinds: bootstrap and service.

All imports are lazy (inside function bodies) to avoid circular import
issues between the compiler, specs, runtime, and registry modules.
This module is called exactly once by load_addons() at CLI startup.
"""

from __future__ import annotations


def _register_builtins() -> None:
    """Register bootstrap and service kinds across all registries."""
    _register_resolvers()
    _register_specs()
    _register_normalizers()
    _register_validators()
    _register_planners()
    _register_step_handlers()
    _register_hooks()
    _register_catalog_entries()


def _register_specs() -> None:
    from loft_cli_core.registry.specs import register_spec_kind
    from loft_cli_core.specs.backup_job_schema import BackupJobSpec
    from loft_cli_core.specs.bootstrap_schema import BootstrapSpec
    from loft_cli_core.specs.compose_project_schema import ComposeProjectSpec
    from loft_cli_core.specs.file_template_schema import FileTemplateSpec
    from loft_cli_core.specs.http_check_schema import HttpCheckSpec
    from loft_cli_core.specs.package_schema import PackageSpec
    from loft_cli_core.specs.postgres_ensure_schema import PostgresEnsureSpec
    from loft_cli_core.specs.service_schema import ServiceSpec
    from loft_cli_core.specs.stack_schema import StackSpec
    from loft_cli_core.specs.systemd_timer_schema import SystemdTimerSpec
    from loft_cli_core.specs.systemd_unit_schema import SystemdUnitSpec

    register_spec_kind("bootstrap", BootstrapSpec)
    register_spec_kind("service", ServiceSpec)
    register_spec_kind("file_template", FileTemplateSpec)
    register_spec_kind("compose_project", ComposeProjectSpec)
    register_spec_kind("stack", StackSpec)
    register_spec_kind("http_check", HttpCheckSpec)
    register_spec_kind("backup_job", BackupJobSpec)
    register_spec_kind("systemd_unit", SystemdUnitSpec)
    register_spec_kind("systemd_timer", SystemdTimerSpec)
    register_spec_kind("postgres_ensure", PostgresEnsureSpec)
    register_spec_kind("package", PackageSpec)


def _register_normalizers() -> None:
    from loft_cli.compiler.normalizer import (
        _normalize_backup_job,
        _normalize_bootstrap,
        _normalize_compose_project,
        _normalize_file_template,
        _normalize_http_check,
        _normalize_package,
        _normalize_postgres_ensure,
        _normalize_service,
        _normalize_stack,
        _normalize_systemd_timer,
        _normalize_systemd_unit,
    )
    from loft_cli_core.registry.normalizers import register_normalizer

    register_normalizer("bootstrap", _normalize_bootstrap)
    register_normalizer("service", _normalize_service)
    register_normalizer("file_template", _normalize_file_template)
    register_normalizer("compose_project", _normalize_compose_project)
    register_normalizer("stack", _normalize_stack)
    register_normalizer("http_check", _normalize_http_check)
    register_normalizer("backup_job", _normalize_backup_job)
    register_normalizer("postgres_ensure", _normalize_postgres_ensure)
    register_normalizer("systemd_unit", _normalize_systemd_unit)
    register_normalizer("systemd_timer", _normalize_systemd_timer)
    register_normalizer("package", _normalize_package)


def _register_validators() -> None:
    from loft_cli_core.registry.validators import register_validator
    from loft_cli_core.specs.validators import (
        validate_backup_job,
        validate_bootstrap,
        validate_compose_project,
        validate_file_template,
        validate_http_check,
        validate_package,
        validate_postgres_ensure,
        validate_service,
        validate_stack,
        validate_systemd_timer,
        validate_systemd_unit,
    )

    register_validator("bootstrap", validate_bootstrap)
    register_validator("service", validate_service)
    register_validator("file_template", validate_file_template)
    register_validator("compose_project", validate_compose_project)
    register_validator("stack", validate_stack)
    register_validator("http_check", validate_http_check)
    register_validator("backup_job", validate_backup_job)
    register_validator("postgres_ensure", validate_postgres_ensure)
    register_validator("systemd_unit", validate_systemd_unit)
    register_validator("systemd_timer", validate_systemd_timer)
    register_validator("package", validate_package)


def _register_planners() -> None:
    from loft_cli.compiler.planner import (
        _plan_backup_job,
        _plan_bootstrap,
        _plan_compose_project,
        _plan_file_template,
        _plan_http_check,
        _plan_package,
        _plan_postgres_ensure,
        _plan_service,
        _plan_stack,
        _plan_systemd_timer,
        _plan_systemd_unit,
    )
    from loft_cli_core.registry.planners import register_planner

    register_planner("bootstrap", _plan_bootstrap)
    register_planner("service", _plan_service)
    register_planner("file_template", _plan_file_template)
    register_planner("compose_project", _plan_compose_project)
    register_planner("stack", _plan_stack)
    register_planner("http_check", _plan_http_check)
    register_planner("backup_job", _plan_backup_job)
    register_planner("postgres_ensure", _plan_postgres_ensure)
    register_planner("systemd_unit", _plan_systemd_unit)
    register_planner("systemd_timer", _plan_systemd_timer)
    register_planner("package", _plan_package)


def _register_step_handlers() -> None:
    from loft_cli_core.plan.models import StepKind
    from loft_cli_core.registry.executors import register_step_handler

    # Wrap Executor instance methods: handler(executor, step) -> StepResult.
    # The executor's private _execute_* methods are left entirely unchanged.
    register_step_handler(StepKind.GATE, lambda ex, step: ex._execute_gate(step))
    register_step_handler(StepKind.SSH_COMMAND, lambda ex, step: ex._execute_ssh_command(step))
    register_step_handler(StepKind.SSH_UPLOAD, lambda ex, step: ex._execute_ssh_upload(step))
    register_step_handler(
        StepKind.LOCAL_FILE_WRITE, lambda ex, step: ex._execute_local_file_write(step)
    )
    register_step_handler(
        StepKind.LOCAL_DB_WRITE, lambda ex, step: ex._execute_local_db_write(step)
    )
    register_step_handler(StepKind.LOCAL_COMMAND, lambda ex, step: ex._execute_local_command(step))
    register_step_handler(StepKind.VERIFY, lambda ex, step: ex._execute_verify(step))
    register_step_handler(
        StepKind.COMPOSE_HEALTH_CHECK,
        lambda ex, step: ex._execute_compose_health_check(step),
    )
    register_step_handler(
        StepKind.COMPOSE_HTTP_READY,
        lambda ex, step: ex._execute_compose_http_ready(step),
    )
    register_step_handler(
        StepKind.POST_DEPLOY_HTTP,
        lambda ex, step: ex._execute_post_deploy_http(step),
    )


def _register_hooks() -> None:
    from loft_cli.local.inventory import (
        record_backup_job_apply,
        record_bootstrap,
        record_compose_project_apply,
        record_file_template_apply,
        record_http_check_apply,
        record_package_apply,
        record_postgres_ensure_apply,
        record_service_apply,
        record_stack_apply,
        record_systemd_timer_apply,
        record_systemd_unit_apply,
    )
    from loft_cli_core.registry.hooks import KindHooks, register_kind_hooks

    register_kind_hooks(
        "bootstrap",
        KindHooks(
            needs_key_generation=True,
            ssh_port_fallback=True,
            on_inventory_record=record_bootstrap,
        ),
    )
    register_kind_hooks(
        "service",
        KindHooks(
            needs_key_generation=False,
            ssh_port_fallback=False,
            on_inventory_record=record_service_apply,
        ),
    )
    register_kind_hooks(
        "file_template",
        KindHooks(
            needs_key_generation=False,
            ssh_port_fallback=False,
            on_inventory_record=record_file_template_apply,
        ),
    )
    register_kind_hooks(
        "compose_project",
        KindHooks(
            needs_key_generation=False,
            ssh_port_fallback=False,
            on_inventory_record=record_compose_project_apply,
        ),
    )
    register_kind_hooks(
        "stack",
        KindHooks(
            needs_key_generation=False,
            ssh_port_fallback=False,
            on_inventory_record=record_stack_apply,
        ),
    )
    register_kind_hooks(
        "http_check",
        KindHooks(
            needs_key_generation=False,
            ssh_port_fallback=False,
            on_inventory_record=record_http_check_apply,
        ),
    )
    register_kind_hooks(
        "backup_job",
        KindHooks(
            needs_key_generation=False,
            ssh_port_fallback=False,
            on_inventory_record=record_backup_job_apply,
        ),
    )
    register_kind_hooks(
        "postgres_ensure",
        KindHooks(
            needs_key_generation=False,
            ssh_port_fallback=False,
            on_inventory_record=record_postgres_ensure_apply,
        ),
    )
    register_kind_hooks(
        "systemd_unit",
        KindHooks(
            needs_key_generation=False,
            ssh_port_fallback=False,
            on_inventory_record=record_systemd_unit_apply,
        ),
    )
    register_kind_hooks(
        "systemd_timer",
        KindHooks(
            needs_key_generation=False,
            ssh_port_fallback=False,
            on_inventory_record=record_systemd_timer_apply,
        ),
    )
    register_kind_hooks(
        "package",
        KindHooks(
            needs_key_generation=False,
            ssh_port_fallback=False,
            on_inventory_record=record_package_apply,
        ),
    )


def _extract_fields_from_model(model_class: type, prefix: str = "") -> list[dict]:
    """Recursively extract field metadata from a Pydantic v2 model class.

    Returns a flat list of dicts with keys: name, type, required, description.
    Nested block fields are recursively expanded with dot-notation names.
    """
    fields: list[dict] = []
    try:
        model_fields = model_class.model_fields
    except AttributeError:
        return fields

    for field_name, field_info in model_fields.items():
        full_name = f"{prefix}.{field_name}" if prefix else field_name
        annotation = field_info.annotation
        required = field_info.is_required()
        description = field_info.description or ""

        # Try to get a clean type string
        try:
            if hasattr(annotation, "__origin__"):
                type_str = str(annotation)
                # Simplify common annotations
                type_str = type_str.replace("typing.", "").replace("Optional[", "").rstrip("]")
            elif annotation is None:
                type_str = "any"
            else:
                type_str = getattr(annotation, "__name__", str(annotation))
        except Exception:
            type_str = str(annotation)

        # Check if the annotation is a nested Pydantic model to expand
        try:
            from pydantic import BaseModel as _BaseModel

            # Get the actual type (unwrap Optional/Union)
            inner_type = annotation
            if hasattr(annotation, "__origin__"):
                args = getattr(annotation, "__args__", ())
                # For Optional[X] (Union[X, None]), get X
                non_none = [a for a in args if a is not type(None)]
                if len(non_none) == 1:
                    inner_type = non_none[0]

            if inner_type and isinstance(inner_type, type) and issubclass(inner_type, _BaseModel):
                # Recurse into nested model — add the block-level entry plus its fields
                fields.append(
                    {
                        "name": full_name,
                        "type": getattr(inner_type, "__name__", str(inner_type)),
                        "required": required,
                        "description": description,
                    }
                )
                # Expand sub-fields only for required/meaningful blocks
                sub_fields = _extract_fields_from_model(inner_type, prefix=full_name)
                fields.extend(sub_fields)
                continue
        except ImportError:
            pass

        fields.append(
            {
                "name": full_name,
                "type": type_str,
                "required": required,
                "description": description,
            }
        )

    return fields


def _register_catalog_entries() -> None:
    """Register catalog entries for all built-in kinds with outputs and field metadata."""
    from loft_cli_core.registry.catalog import (
        CatalogEntry,
        OutputTemplate,
        register_catalog_entry,
    )
    from loft_cli_core.specs.backup_job_schema import BackupJobSpec
    from loft_cli_core.specs.bootstrap_schema import BootstrapSpec
    from loft_cli_core.specs.compose_project_schema import ComposeProjectSpec
    from loft_cli_core.specs.file_template_schema import FileTemplateSpec
    from loft_cli_core.specs.http_check_schema import HttpCheckSpec
    from loft_cli_core.specs.package_schema import PackageSpec
    from loft_cli_core.specs.postgres_ensure_schema import PostgresEnsureSpec
    from loft_cli_core.specs.service_schema import ServiceSpec
    from loft_cli_core.specs.stack_schema import StackSpec
    from loft_cli_core.specs.systemd_timer_schema import SystemdTimerSpec
    from loft_cli_core.specs.systemd_unit_schema import SystemdUnitSpec

    # bootstrap
    register_catalog_entry(
        "bootstrap",
        CatalogEntry(
            kind="bootstrap",
            description=(
                "Harden a fresh Debian/Ubuntu host: SSH hardening, firewall, "
                "admin user setup, and optional WireGuard VPN."
            ),
            fields=_extract_fields_from_model(BootstrapSpec),
            outputs=[
                OutputTemplate(
                    name="ssh_alias",
                    description="SSH Host alias to connect to this host after bootstrap.",
                    example="ssh {provider}--{host.name}  # e.g. ssh hetzner--dev-vps",
                ),
                OutputTemplate(
                    name="ssh_port",
                    description="SSH port as configured by the bootstrap spec.",
                    example="2222",
                ),
            ],
        ),
    )

    # service
    register_catalog_entry(
        "service",
        CatalogEntry(
            kind="service",
            description=(
                "Install and configure services on a bootstrapped host: "
                "PostgreSQL, Nginx, Docker, and individual containers."
            ),
            fields=_extract_fields_from_model(ServiceSpec),
            outputs=[
                OutputTemplate(
                    name="postgres_host",
                    description="Hostname of the PostgreSQL server (when postgres is enabled).",
                    example="localhost",
                ),
                OutputTemplate(
                    name="postgres_port",
                    description="Port PostgreSQL is listening on (when postgres is enabled).",
                    example="5432",
                ),
                OutputTemplate(
                    name="postgres_database",
                    description="Name of the created database (when postgres.create_database is set).",
                    example="{postgres.create_database.name}  # e.g. myapp",
                ),
                OutputTemplate(
                    name="postgres_user",
                    description="Name of the created role (when postgres.create_role is set).",
                    example="{postgres.create_role.name}  # e.g. myapp_user",
                ),
                OutputTemplate(
                    name="nginx_site_url",
                    description="URL of the configured Nginx site (when nginx sites are declared).",
                    example="http://{nginx.sites[0].domain}",
                ),
            ],
        ),
    )

    # file_template
    register_catalog_entry(
        "file_template",
        CatalogEntry(
            kind="file_template",
            description=(
                "Render Jinja2 templates and upload managed configuration files to a remote host."
            ),
            fields=_extract_fields_from_model(FileTemplateSpec),
        ),
    )

    # compose_project
    register_catalog_entry(
        "compose_project",
        CatalogEntry(
            kind="compose_project",
            description=(
                "Deploy a Docker Compose project: upload files, pull images, "
                "start the stack, and verify health."
            ),
            fields=_extract_fields_from_model(ComposeProjectSpec),
            outputs=[
                OutputTemplate(
                    name="project_dir",
                    description="Remote directory where the compose project files are uploaded.",
                    example="{project.directory}  # e.g. /opt/myapp",
                ),
            ],
        ),
    )

    # stack
    register_catalog_entry(
        "stack",
        CatalogEntry(
            kind="stack",
            description=(
                "Group related resources into a single deployable application boundary, "
                "executed in dependency order."
            ),
            fields=_extract_fields_from_model(StackSpec),
        ),
    )

    # http_check
    register_catalog_entry(
        "http_check",
        CatalogEntry(
            kind="http_check",
            description=(
                "GET-only HTTP readiness probe with configurable retry and timeout. "
                "Usable as a dependency gate in stacks."
            ),
            fields=_extract_fields_from_model(HttpCheckSpec),
        ),
    )

    # backup_job
    register_catalog_entry(
        "backup_job",
        CatalogEntry(
            kind="backup_job",
            description=(
                "Define host-local backup operations (PostgreSQL dumps or directory backups) "
                "with retention and scheduling via systemd timer."
            ),
            fields=_extract_fields_from_model(BackupJobSpec),
        ),
    )

    # systemd_unit
    register_catalog_entry(
        "systemd_unit",
        CatalogEntry(
            kind="systemd_unit",
            description=(
                "Deploy and manage a host-native systemd service from structured declarations."
            ),
            fields=_extract_fields_from_model(SystemdUnitSpec),
            outputs=[
                OutputTemplate(
                    name="unit_name",
                    description="The .service unit name as installed on the server.",
                    example="{unit.unit_name}.service  # e.g. myapp.service",
                ),
            ],
        ),
    )

    # systemd_timer
    register_catalog_entry(
        "systemd_timer",
        CatalogEntry(
            kind="systemd_timer",
            description=(
                "Deploy scheduled execution via systemd timers: generates a .timer "
                "and companion oneshot .service unit."
            ),
            fields=_extract_fields_from_model(SystemdTimerSpec),
        ),
    )

    # postgres_ensure
    register_catalog_entry(
        "postgres_ensure",
        CatalogEntry(
            kind="postgres_ensure",
            description=(
                "Ensure PostgreSQL resources exist: users, databases, extensions, "
                "and privilege grants."
            ),
            fields=_extract_fields_from_model(PostgresEnsureSpec),
            outputs=[
                OutputTemplate(
                    name="database_url",
                    description="Connection string for the ensured PostgreSQL database.",
                    example=(
                        "postgres://{users[0].name}:***@{connection.host}:"
                        "{connection.port}/{databases[0].name}"
                    ),
                ),
            ],
        ),
    )

    # package
    register_catalog_entry(
        "package",
        CatalogEntry(
            kind="package",
            description=(
                "Install or remove system packages on a remote host using the "
                "native package manager (apt, yum/dnf)."
            ),
            fields=_extract_fields_from_model(PackageSpec),
        ),
    )


def _register_resolvers() -> None:
    """Register the built-in value resolvers: 'env' and 'file'."""
    import os
    from pathlib import Path

    from loft_cli_core.registry.resolvers import register_resolver

    def _resolve_env(key: str) -> str | None:
        return os.environ.get(key)

    def _resolve_file(key: str) -> str | None:
        path = Path(key).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        if not path.exists():
            return None
        content = path.read_text(encoding="utf-8")
        # Strip a single trailing newline — common in key files, config files, etc.
        return content.rstrip("\n")

    register_resolver("env", _resolve_env)
    register_resolver("file", _resolve_file)
