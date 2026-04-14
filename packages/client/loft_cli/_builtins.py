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
    from loft_cli_core.specs.blueprint_schema import BlueprintSpec
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
    register_spec_kind("blueprint", BlueprintSpec)


def _register_normalizers() -> None:
    from loft_cli.compiler.normalizer import (
        _normalize_backup_job,
        _normalize_blueprint,
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
    register_normalizer("blueprint", _normalize_blueprint)


def _register_validators() -> None:
    from loft_cli_core.registry.validators import register_validator
    from loft_cli_core.specs.validators import (
        validate_backup_job,
        validate_blueprint,
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
    register_validator("blueprint", validate_blueprint)


def _register_planners() -> None:
    from loft_cli.compiler.planner import (
        _plan_backup_job,
        _plan_blueprint,
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
    register_planner("blueprint", _plan_blueprint)


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
    register_kind_hooks(
        "blueprint",
        KindHooks(
            needs_key_generation=False,
            ssh_port_fallback=False,
            on_inventory_record=record_stack_apply,  # blueprints expand like stacks
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
        StepTemplate,
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
            step_templates=[
                StepTemplate(
                    id="apt_update",
                    description="Refresh apt package index",
                    code_block="apt-get update -y",
                ),
                StepTemplate(
                    id="install_packages",
                    description="Install baseline packages (ufw, wireguard, etc.)",
                    code_block="DEBIAN_FRONTEND=noninteractive apt-get install -y <packages>",
                ),
                StepTemplate(
                    id="create_admin_user",
                    description="Create admin user and add to sudo/docker groups",
                    code_block=(
                        "addgroup <admin_user>\n"
                        "adduser --disabled-password --gecos '' "
                        "--ingroup <admin_user> <admin_user>\n"
                        "usermod -aG sudo,docker <admin_user>"
                    ),
                ),
                StepTemplate(
                    id="install_authorized_keys",
                    description="Install SSH public key for admin user",
                    code_block=(
                        "mkdir -p /home/<admin_user>/.ssh\n"
                        "printf '%s\\n' '<pubkey>' "
                        ">> /home/<admin_user>/.ssh/authorized_keys\n"
                        "chmod 700 /home/<admin_user>/.ssh\n"
                        "chmod 600 /home/<admin_user>/.ssh/authorized_keys\n"
                        "chown -R <admin_user>:<admin_user> /home/<admin_user>/.ssh"
                    ),
                ),
                StepTemplate(
                    id="nopasswd_sudoers",
                    description="Grant passwordless sudo to admin user",
                    code_block=(
                        "echo '<admin_user> ALL=(ALL) NOPASSWD:ALL' "
                        "> /etc/sudoers.d/<admin_user>\n"
                        "chmod 440 /etc/sudoers.d/<admin_user>"
                    ),
                ),
                StepTemplate(
                    id="configure_ssh_port",
                    description="Set custom SSH port in sshd_config",
                    code_block=(
                        "cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak\n"
                        "sed -i 's/^#\\?Port .*/Port <ssh_port>/' "
                        "/etc/ssh/sshd_config"
                    ),
                ),
                StepTemplate(
                    id="reload_sshd",
                    description="Reload sshd (handles socket-activated Ubuntu 24.04+)",
                    code_block=(
                        "if systemctl is-active ssh.socket >/dev/null 2>&1; then\n"
                        "  systemctl daemon-reload && systemctl restart ssh.socket\n"
                        "else\n"
                        "  systemctl reload ssh || systemctl reload sshd\n"
                        "fi"
                    ),
                ),
                StepTemplate(
                    id="verify_admin_login_on_new_port",
                    description="Gate: verify admin SSH key login works on the new port before locking down root",
                    code_block="ssh -p <ssh_port> <admin_user>@<host> 'echo ok'",
                ),
                StepTemplate(
                    id="disable_root_login",
                    description="Disable root SSH login (runs only after gate passes)",
                    code_block=(
                        "sed -i 's/^#\\?PermitRootLogin.*/PermitRootLogin no/' "
                        "/etc/ssh/sshd_config"
                    ),
                ),
                StepTemplate(
                    id="disable_password_auth",
                    description="Disable password auth (runs only after gate passes)",
                    code_block=(
                        "sed -i 's/^#\\?PasswordAuthentication.*/"
                        "PasswordAuthentication no/' /etc/ssh/sshd_config"
                    ),
                ),
                StepTemplate(
                    id="enable_firewall",
                    description="Enable UFW with default-deny incoming policy",
                    code_block=(
                        "ufw default deny incoming\n"
                        "ufw default allow outgoing\n"
                        "ufw allow <ssh_port>/tcp\n"
                        "ufw --force enable"
                    ),
                ),
                StepTemplate(
                    id="configure_wireguard",
                    description="Install WireGuard config and bring up tunnel",
                    condition={"field": "wireguard.enabled", "equals": True},
                    code_block=(
                        "install -m 600 /dev/stdin /etc/wireguard/<iface>.conf "
                        "<< 'EOF'\n"
                        "[Interface]\n"
                        "PrivateKey = <server_private_key>\n"
                        "Address = <server_vpn_ip>/24\n"
                        "ListenPort = <wg_port>\n"
                        "[Peer]\n"
                        "PublicKey = <client_public_key>\n"
                        "AllowedIPs = <client_vpn_ip>/32\n"
                        "EOF\n"
                        "systemctl enable --now wg-quick@<iface>"
                    ),
                ),
            ],
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
            step_templates=[
                StepTemplate(
                    id="install_postgres",
                    description="Install PostgreSQL server",
                    condition={"field": "postgres", "present": True},
                    code_block=(
                        "DEBIAN_FRONTEND=noninteractive apt-get install -y "
                        "postgresql-<postgres_version>"
                    ),
                ),
                StepTemplate(
                    id="create_postgres_role",
                    description="Create PostgreSQL role with login password",
                    condition={"field": "postgres.create_role", "present": True},
                    code_block=(
                        'sudo -u postgres psql -c "'
                        "CREATE ROLE <role_name> LOGIN PASSWORD '<password>';\""
                    ),
                ),
                StepTemplate(
                    id="create_postgres_database",
                    description="Create PostgreSQL database owned by role",
                    condition={"field": "postgres.create_database", "present": True},
                    code_block="sudo -u postgres createdb -O <owner> <database_name>",
                ),
                StepTemplate(
                    id="install_docker",
                    description="Install Docker Engine via official script",
                    condition={"field": "docker", "present": True},
                    code_block=(
                        "curl -fsSL https://get.docker.com | sh\n" "systemctl enable --now docker"
                    ),
                ),
                StepTemplate(
                    id="pull_image",
                    description="Pull container image from registry",
                    condition={"field": "containers", "present": True},
                    code_block="docker pull <image>:<tag>",
                ),
                StepTemplate(
                    id="run_container",
                    description="Start a detached container with configured ports, volumes, env",
                    condition={"field": "containers", "present": True},
                    code_block=(
                        "docker run -d --name <container_name> \\\n"
                        "  --restart unless-stopped \\\n"
                        "  -p <host_port>:<container_port> \\\n"
                        "  -v <host_path>:<container_path> \\\n"
                        "  -e KEY=<value> \\\n"
                        "  <image>:<tag>"
                    ),
                ),
                StepTemplate(
                    id="install_nginx",
                    description="Install Nginx web server",
                    condition={"field": "nginx", "present": True},
                    code_block="DEBIAN_FRONTEND=noninteractive apt-get install -y nginx",
                ),
                StepTemplate(
                    id="configure_nginx_site",
                    description="Write Nginx site config and reload",
                    condition={"field": "nginx.sites", "present": True},
                    code_block=(
                        "# upload: /etc/nginx/sites-available/<site_name>\n"
                        "server {\n"
                        "  listen 80;\n"
                        "  server_name <domain>;\n"
                        "  location / { proxy_pass http://<upstream>; }\n"
                        "}\n"
                        "ln -sf /etc/nginx/sites-available/<site_name> "
                        "/etc/nginx/sites-enabled/<site_name>\n"
                        "nginx -t && systemctl reload nginx"
                    ),
                ),
            ],
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
            step_templates=[
                StepTemplate(
                    id="mkdir_target_dir",
                    description="Ensure target directory exists",
                    code_block="mkdir -p <target_dir>",
                ),
                StepTemplate(
                    id="upload_rendered_template",
                    description="Write rendered template content to target path",
                    code_block=(
                        "# upload: <target_path>\n"
                        "# rendered from <template_path> with variables "
                        "<vars>\n"
                        "<rendered_content>"
                    ),
                ),
                StepTemplate(
                    id="set_permissions",
                    description="Apply owner and mode to the uploaded file",
                    code_block=(
                        "chown <owner>:<group> <target_path>\n" "chmod <mode> <target_path>"
                    ),
                ),
            ],
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
            step_templates=[
                StepTemplate(
                    id="mkdir_project_dir",
                    description="Create the remote project directory",
                    code_block="mkdir -p <project_directory>",
                ),
                StepTemplate(
                    id="upload_compose_file",
                    description="Upload the docker-compose.yml to the project directory",
                    code_block=(
                        "# upload: <project_directory>/<compose_file>\n"
                        "<contents of user-provided docker-compose.yml>"
                    ),
                ),
                StepTemplate(
                    id="upload_templates",
                    description="Render and upload Jinja2 templates (e.g. .env)",
                    condition={"field": "project.templates", "present": True},
                    code_block=(
                        "# upload: <project_directory>/<rendered_filename>\n"
                        "<rendered content from template + variables>"
                    ),
                ),
                StepTemplate(
                    id="compose_config_validate",
                    description="Validate compose file syntax",
                    code_block=(
                        "cd <project_directory> && "
                        "docker compose -f <compose_file> -p <project_name> "
                        "config --quiet"
                    ),
                ),
                StepTemplate(
                    id="compose_pull",
                    description="Pull images declared in the compose file",
                    condition={"field": "project.pull_before_up", "equals": True},
                    code_block=(
                        "cd <project_directory> && "
                        "docker compose -f <compose_file> -p <project_name> pull"
                    ),
                ),
                StepTemplate(
                    id="compose_up",
                    description="Start the stack in detached mode",
                    code_block=(
                        "cd <project_directory> && "
                        "docker compose -f <compose_file> -p <project_name> "
                        "up -d"
                    ),
                ),
                StepTemplate(
                    id="compose_health_check",
                    description="Poll `docker compose ps` until all containers report healthy",
                    code_block=(
                        "docker compose -f <compose_file> -p <project_name> "
                        "ps --format json\n"
                        "# retry every <interval>s up to <timeout>s, require all "
                        "containers State=running and Health=healthy"
                    ),
                ),
                StepTemplate(
                    id="http_ready_probe",
                    description="Poll application URL until it returns expected status",
                    condition={"field": "project.healthcheck.http_ready", "present": True},
                    code_block=(
                        "curl -fsS -o /dev/null -w '%{http_code}' <url>\n"
                        "# expect <expected_status>, retry <retries> times "
                        "every <interval>s"
                    ),
                ),
                StepTemplate(
                    id="post_deploy_shell",
                    description="Run shell command after deploy (post_deploy action)",
                    condition={"field": "project.post_deploy", "present": True},
                    code_block="bash -c '<command>'",
                ),
                StepTemplate(
                    id="post_deploy_container_exec",
                    description="Run command inside a container after deploy",
                    condition={"field": "project.post_deploy", "present": True},
                    code_block="docker exec <container> <command>",
                ),
            ],
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
            step_templates=[
                StepTemplate(
                    id="resolve_dependency_order",
                    description="Topological sort child resources by declared depends_on",
                    code_block=(
                        "# local (client-side): topological sort of "
                        "resources[] by depends_on\n"
                        "# emits a flat Plan where each child's steps are "
                        "inserted in order"
                    ),
                ),
                StepTemplate(
                    id="execute_child_resources",
                    description="Run each child resource's plan sequentially",
                    code_block=(
                        "# for each child resource in dependency order:\n"
                        "#   dispatch to the child's kind planner + executor\n"
                        "#   abort stack if any child fails"
                    ),
                ),
            ],
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
            step_templates=[
                StepTemplate(
                    id="http_get_with_retry",
                    description="GET url, retry until expected status or timeout",
                    code_block=(
                        "curl -fsS -o /dev/null -w '%{http_code}' <url>\n"
                        "# retry <retries> times every <interval>s, "
                        "expect status <expected_status>"
                    ),
                ),
            ],
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
            step_templates=[
                StepTemplate(
                    id="mkdir_backup_dir",
                    description="Create backup destination directory",
                    code_block="mkdir -p <backup_dir>",
                ),
                StepTemplate(
                    id="write_backup_script",
                    description="Install the backup script (postgres_dump or directory rsync/tar)",
                    code_block=(
                        "# upload: /usr/local/bin/<job_name>.sh\n"
                        "# for postgres_dump:\n"
                        "pg_dump -U <user> -h <host> -p <port> <database> \\\n"
                        "  | gzip > <backup_dir>/<database>-$(date +%F-%H%M).sql.gz\n"
                        "# for directory:\n"
                        "tar -czf <backup_dir>/<name>-$(date +%F-%H%M).tar.gz "
                        "<source_path>"
                    ),
                ),
                StepTemplate(
                    id="apply_retention",
                    description="Delete backups older than retention window",
                    code_block=("find <backup_dir> -type f -mtime +<retention_days> " "-delete"),
                ),
                StepTemplate(
                    id="install_systemd_timer",
                    description="Install the systemd timer + oneshot service for scheduled runs",
                    code_block=(
                        "# upload: /etc/systemd/system/<job_name>.service\n"
                        "[Service]\nType=oneshot\n"
                        "ExecStart=/usr/local/bin/<job_name>.sh\n\n"
                        "# upload: /etc/systemd/system/<job_name>.timer\n"
                        "[Timer]\nOnCalendar=<schedule>\nPersistent=true\n\n"
                        "systemctl daemon-reload\n"
                        "systemctl enable --now <job_name>.timer"
                    ),
                ),
            ],
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
            step_templates=[
                StepTemplate(
                    id="upload_service_unit",
                    description="Write the .service unit file to /etc/systemd/system",
                    code_block=(
                        "# upload: /etc/systemd/system/<unit_name>.service\n"
                        "[Unit]\nDescription=<description>\n\n"
                        "[Service]\nType=<service_type>\n"
                        "ExecStart=<exec_start>\nRestart=<restart>\n"
                        "User=<user>\n\n"
                        "[Install]\nWantedBy=multi-user.target"
                    ),
                ),
                StepTemplate(
                    id="upload_logrotate_config",
                    description="Install optional logrotate config",
                    condition={"field": "unit.logrotate", "present": True},
                    code_block=(
                        "# upload: /etc/logrotate.d/<unit_name>\n"
                        "<log_path> {\n"
                        "  rotate <rotate_count>\n"
                        "  <frequency>\n"
                        "  compress\n"
                        "  missingok\n"
                        "  notifempty\n"
                        "}"
                    ),
                ),
                StepTemplate(
                    id="daemon_reload_and_enable",
                    description="Reload systemd and enable+start the service",
                    code_block=(
                        "systemctl daemon-reload\n" "systemctl enable --now <unit_name>.service"
                    ),
                ),
            ],
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
            step_templates=[
                StepTemplate(
                    id="upload_oneshot_service",
                    description="Write the oneshot .service unit triggered by the timer",
                    code_block=(
                        "# upload: /etc/systemd/system/<timer_name>.service\n"
                        "[Unit]\nDescription=<description>\n\n"
                        "[Service]\nType=oneshot\n"
                        "ExecStart=<exec_start>\n"
                        "User=<user>"
                    ),
                ),
                StepTemplate(
                    id="upload_timer_unit",
                    description="Write the .timer unit with schedule",
                    code_block=(
                        "# upload: /etc/systemd/system/<timer_name>.timer\n"
                        "[Unit]\nDescription=<description>\n\n"
                        "[Timer]\nOnCalendar=<schedule>\nPersistent=true\n\n"
                        "[Install]\nWantedBy=timers.target"
                    ),
                ),
                StepTemplate(
                    id="daemon_reload_and_enable_timer",
                    description="Reload systemd and enable+start the timer",
                    code_block=(
                        "systemctl daemon-reload\n" "systemctl enable --now <timer_name>.timer"
                    ),
                ),
            ],
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
            step_templates=[
                StepTemplate(
                    id="ensure_user",
                    description="Create or update a PostgreSQL role idempotently",
                    code_block=(
                        'sudo -u postgres psql -d postgres -c "\n'
                        "  DO \\$\\$ BEGIN\n"
                        "    IF NOT EXISTS (SELECT FROM pg_roles "
                        "WHERE rolname='<user>') THEN\n"
                        "      CREATE ROLE <user> LOGIN PASSWORD '<password>';\n"
                        "    ELSE\n"
                        "      ALTER ROLE <user> PASSWORD '<password>';\n"
                        "    END IF;\n"
                        "  END \\$\\$;\n"
                        '"'
                    ),
                ),
                StepTemplate(
                    id="ensure_database",
                    description="Create database if missing, owned by user",
                    code_block=(
                        "sudo -u postgres psql -tc "
                        "\"SELECT 1 FROM pg_database WHERE datname='<database>'\" "
                        "| grep -q 1 || "
                        "sudo -u postgres createdb -O <owner> <database>"
                    ),
                ),
                StepTemplate(
                    id="ensure_extension",
                    description="Install a PostgreSQL extension in a database",
                    code_block=(
                        "sudo -u postgres psql -d <database> -c "
                        '"CREATE EXTENSION IF NOT EXISTS <extension>;"'
                    ),
                ),
                StepTemplate(
                    id="ensure_grant",
                    description="Grant privileges on a database/schema to a role",
                    code_block=(
                        "sudo -u postgres psql -d <database> -c "
                        '"GRANT <privileges> ON <object> TO <role>;"'
                    ),
                ),
            ],
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
            step_templates=[
                StepTemplate(
                    id="apt_install",
                    description="Install packages via apt (state=present)",
                    condition={"field": "state", "equals": "present"},
                    code_block=(
                        "apt-get update -y\n"
                        "DEBIAN_FRONTEND=noninteractive apt-get install -y "
                        "<packages>"
                    ),
                ),
                StepTemplate(
                    id="apt_remove",
                    description="Remove packages via apt (state=absent)",
                    condition={"field": "state", "equals": "absent"},
                    code_block=("DEBIAN_FRONTEND=noninteractive apt-get remove -y " "<packages>"),
                ),
            ],
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
