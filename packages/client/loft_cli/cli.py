"""loft-cli CLI — commands wiring the full pipeline.

validate   <spec.yaml>
plan       <spec.yaml>
docs       <spec.yaml> [--output FILE] [--mode guide|commands]
diff       <spec.yaml>
doctor     <spec.yaml>  — drift detection
doctor     --fleet <dir> [--selector <expr>]  — fleet drift summary
reconcile  <spec.yaml>  — bring server back to desired state
apply      <spec.yaml> [--dry-run]
apply      --fleet <dir> [--selector <expr>] [--continue-on-error]  — fleet apply
inspect    run <run-id>
inventory  list | show <server-id>
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from loft_cli.local.inventory_db import InventoryDB

app = typer.Typer(
    name="loft-cli",
    help=(
        "Securely bootstrap Linux servers into production-ready nodes — "
        "with auditable plans, generated ops docs, and encrypted local inventory."
    ),
    no_args_is_help=True,
    add_completion=True,
)
inventory_app = typer.Typer(help="Manage local server inventory.", no_args_is_help=True)
inspect_app = typer.Typer(help="Inspect apply runs.", no_args_is_help=True)
tunnel_app = typer.Typer(help="Manage WireGuard tunnels.", no_args_is_help=True)
catalog_app = typer.Typer(help="Introspect the loft-cli feature catalog.", no_args_is_help=True)
app.add_typer(inventory_app, name="inventory")
app.add_typer(inspect_app, name="inspect")
app.add_typer(tunnel_app, name="tunnel")
app.add_typer(catalog_app, name="catalog")

console = Console()


@app.callback()
def _startup() -> None:
    """Load built-in kinds and any installed addons before running a command."""
    from loft_cli_core.registry import load_addons

    load_addons()


def _parse_identifier(identifier: str) -> tuple[str | None, str]:
    """Parse identifier into (provider, host_name).

    Supports:
    - "host" -> (None, "host")
    - "provider/host" -> ("provider", "host")
    """
    if "/" in identifier:
        parts = identifier.split("/", 1)
        return parts[0], parts[1]
    return None, identifier


# ------------------------------------------------------------------ #
# version
# ------------------------------------------------------------------ #


@app.command()
def version(
    host: str | None = typer.Option(
        None, "--host", help="Also check agent version on a remote host"
    ),
    port: int = typer.Option(22, "--port", help="SSH port for remote agent check"),
    user: str = typer.Option("root", "--user", help="SSH user for remote agent check"),
    key: str | None = typer.Option(None, "--key", help="SSH key path for remote agent check"),
) -> None:
    """Print client version (and optionally agent version on a remote host)."""
    from loft_cli import __version__

    console.print(f"loft-cli client: {__version__}")

    if host:
        from loft_cli.agent_installer import detect_agent
        from loft_cli.runtime.fabric_transport import FabricTransport

        try:
            transport = FabricTransport(host=host, user=user, port=port, key_path=key)
            agent_version = detect_agent(transport)
            if agent_version:
                console.print(f"loft-cli agent:  {agent_version} (on {host})")
            else:
                console.print(f"loft-cli agent:  [dim]not installed[/dim] (on {host})")
            transport.close()
        except Exception as e:
            console.print(f"loft-cli agent:  [red]unreachable[/red] ({e})")


# ------------------------------------------------------------------ #
# update
# ------------------------------------------------------------------ #


@app.command()
def update() -> None:
    """Check for updates and self-update the loft-cli client."""
    from loft_cli.updater import self_update

    self_update(console=console)


@app.command(name="agent-update")
def agent_update(
    host: str = typer.Argument(..., help="Target host to update the agent on"),
    port: int = typer.Option(22, "--port", help="SSH port"),
    user: str = typer.Option("root", "--user", help="SSH user"),
    key: str | None = typer.Option(None, "--key", help="SSH key path"),
) -> None:
    """Update the loft-cli-agent binary on a remote host."""
    from loft_cli.runtime.fabric_transport import FabricTransport
    from loft_cli.updater import update_agent

    transport = FabricTransport(host=host, user=user, port=port, key_path=key)
    try:
        update_agent(transport, console=console)
    finally:
        transport.close()


def _build_pipeline(
    spec_path: Path,
    ensure_keys: bool = False,
    *,
    strict_env: bool = True,
    env_file: list[Path] | None = None,
):
    """Run Parse → Validate → (KeyGen) → Normalize → Plan.

    Returns (spec, ctx, plan, issues) for single-document specs.
    Returns (specs, ctxs, plans, all_issues) for multi-document specs.
    """
    from loft_cli.compiler.normalizer import normalize
    from loft_cli.compiler.parser import parse
    from loft_cli.compiler.planner import plan as make_plan
    from loft_cli_core.registry import get_kind_hooks
    from loft_cli_core.specs.validators import validate_spec

    parsed = parse(spec_path, strict_env=strict_env, env_files=env_file)

    # Multi-document support: process each spec independently
    if isinstance(parsed, list):
        specs = []
        ctxs = []
        plans = []
        all_issues = []
        for spec in parsed:
            issues = validate_spec(spec)
            all_issues.extend(issues)
            if ensure_keys and get_kind_hooks(spec.kind).needs_key_generation:
                from loft_cli.local.keys import ensure_admin_keys

                ensure_admin_keys(spec, console=console)
            ctx = normalize(spec, spec_dir=spec_path.resolve().parent)
            p = make_plan(ctx)
            specs.append(spec)
            ctxs.append(ctx)
            plans.append(p)
        return specs, ctxs, plans, all_issues

    # Single document (backward compatible)
    spec = parsed
    issues = validate_spec(spec)

    if ensure_keys and get_kind_hooks(spec.kind).needs_key_generation:
        from loft_cli.local.keys import ensure_admin_keys

        ensure_admin_keys(spec, console=console)

    ctx = normalize(spec, spec_dir=spec_path.resolve().parent)
    p = make_plan(ctx)
    return spec, ctx, p, issues


def _print_issues(issues, stop_on_error: bool = True) -> None:
    from loft_cli_core.specs.validators import has_errors

    for issue in issues:
        color = "red" if issue.severity == "error" else "yellow"
        console.print(f"  [{color}]{issue}[/{color}]")

    if stop_on_error and has_errors(issues):
        console.print("\n[bold red]Validation errors found. Fix before applying.[/bold red]")
        raise typer.Exit(1)


# ------------------------------------------------------------------ #
# validate
# ------------------------------------------------------------------ #


@app.command()
def validate(
    spec: Path = typer.Argument(..., help="Path to YAML spec file", exists=True),
    env_file: list[Path] | None = typer.Option(
        None, "--env-file", help="Load environment variables from .env file(s) (repeatable)"
    ),
    passthrough: bool = typer.Option(
        False,
        "--passthrough",
        help="Leave unresolved ${VAR} references unchanged instead of erroring",
    ),
) -> None:
    """Validate a YAML spec file against its schema."""
    from loft_cli.compiler.parser import parse
    from loft_cli_core.specs.validators import has_errors, validate_spec

    console.print(f"[bold]Validating:[/bold] {spec}")
    try:
        parsed = parse(spec, strict_env=not passthrough, env_files=env_file)
    except Exception as e:
        console.print(f"[bold red]Parse error:[/bold red] {e}")
        raise typer.Exit(1) from None

    # Handle multi-document specs
    specs_list = parsed if isinstance(parsed, list) else [parsed]
    all_issues = []
    for i, s in enumerate(specs_list):
        if len(specs_list) > 1:
            console.print(f"\n[bold]Document {i + 1}:[/bold] {s.meta.name} ({s.kind})")
        issues = validate_spec(s)
        all_issues.extend(issues)

    if not all_issues:
        doc_label = f"{len(specs_list)} document(s)" if len(specs_list) > 1 else "Spec"
        console.print(f"[bold green]✓ {doc_label} valid.[/bold green]")
    else:
        _print_issues(all_issues, stop_on_error=False)
        if has_errors(all_issues):
            raise typer.Exit(1)


# ------------------------------------------------------------------ #
# plan
# ------------------------------------------------------------------ #


@app.command()
def plan(
    spec: Path = typer.Argument(..., help="Path to YAML spec file", exists=True),
    env_file: list[Path] | None = typer.Option(
        None, "--env-file", help="Load environment variables from .env file(s) (repeatable)"
    ),
    passthrough: bool = typer.Option(
        False,
        "--passthrough",
        help="Leave unresolved ${VAR} references unchanged instead of erroring",
    ),
) -> None:
    """Show the execution plan for a spec without applying it."""
    from loft_cli_core.plan.render_text import render_plan

    try:
        result = _build_pipeline(spec, strict_env=not passthrough, env_file=env_file)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1) from None

    specs_r, _, plans_r, issues = result

    if issues:
        console.print("[bold yellow]Validation warnings:[/bold yellow]")
        _print_issues(issues, stop_on_error=True)

    # Handle multi-doc: plans_r may be a list or a single Plan
    plans_list = plans_r if isinstance(plans_r, list) else [plans_r]
    for p in plans_list:
        render_plan(p, console=console)


# ------------------------------------------------------------------ #
# diff
# ------------------------------------------------------------------ #


@app.command(name="diff")
def diff_cmd(
    spec: Path = typer.Argument(..., help="Path to YAML spec file", exists=True),
    env_file: list[Path] | None = typer.Option(
        None, "--env-file", help="Load environment variables from .env file(s) (repeatable)"
    ),
    passthrough: bool = typer.Option(
        False,
        "--passthrough",
        help="Leave unresolved ${VAR} references unchanged instead of erroring",
    ),
) -> None:
    """Show what would change on the server before applying."""
    from loft_cli.agent_installer import detect_agent
    from loft_cli.runtime.fabric_transport import FabricTransport
    from loft_cli_core.plan.render_diff import render_diff
    from loft_cli_core.state import RuntimeState

    try:
        parsed_spec, ctx, p, issues = _build_pipeline(
            spec, strict_env=not passthrough, env_file=env_file
        )
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1) from None

    if issues:
        _print_issues(issues, stop_on_error=True)

    # Try to retrieve runtime state from the target
    current_state = None
    try:
        login = parsed_spec.login
        key_path = (
            str(ctx.login_key_path) if ctx.login_key_path and ctx.login_key_path.exists() else None
        )
        transport = FabricTransport(
            host=parsed_spec.host.address,
            user=login.user,
            port=login.port,
            key_path=key_path,
            password=ctx.login_password,
        )

        agent_version = detect_agent(transport)
        if agent_version:
            state_content = transport.download("/var/lib/loft-cli/runtime-state.json")
            current_state = RuntimeState.model_validate_json(state_content)
            console.print(f"[dim]Agent v{agent_version} — loaded runtime state[/dim]")
        else:
            console.print("[dim]No agent installed — showing full plan as new[/dim]")
        transport.close()
    except Exception:
        console.print("[dim]Could not retrieve runtime state — showing full plan as new[/dim]")

    render_diff(p, current_state, console=console)


# ------------------------------------------------------------------ #
# doctor
# ------------------------------------------------------------------ #


def _run_doctor_on_spec(parsed_spec, ctx, p, console) -> dict:
    """Run the doctor check for a single spec.

    Returns a result dict with keys:
        status  : "clean" | "drift" | "error"
        drifted : list[str]  — drifted resource names
        error   : str | None — error message if status == "error"
    """
    from loft_cli.agent_installer import detect_agent
    from loft_cli.runtime.fabric_transport import FabricTransport

    try:
        login = parsed_spec.login
        key_path = (
            str(ctx.login_key_path) if ctx.login_key_path and ctx.login_key_path.exists() else None
        )
        transport = FabricTransport(
            host=parsed_spec.host.address,
            user=login.user,
            port=login.port,
            key_path=key_path,
            password=ctx.login_password,
        )

        agent_version = detect_agent(transport)
        if not agent_version:
            console.print(
                "[yellow]Agent not found on target server — attempting automatic install...[/yellow]"
            )
            from loft_cli.updater import update_agent

            installed = update_agent(transport, console=console)
            if not installed:
                transport.close()
                return {
                    "status": "error",
                    "drifted": [],
                    "error": "Agent not installed and auto-install failed",
                }
            agent_version = detect_agent(transport)
            if not agent_version:
                transport.close()
                return {
                    "status": "error",
                    "drifted": [],
                    "error": "Agent installed but could not be detected",
                }

        from loft_cli_core.agent_paths import AGENT_BINARY_PATH, AGENT_DESIRED_DIR

        plan_json = p.model_dump_json(indent=2)
        plan_remote_path = f"{AGENT_DESIRED_DIR}/doctor-plan.json"
        transport.upload_content(plan_json, plan_remote_path, sudo=True)

        result = transport.run(
            f"{AGENT_BINARY_PATH} doctor {plan_remote_path}",
            sudo=True,
            warn=True,
        )

        if result.stdout:
            console.print(result.stdout.rstrip())
        if result.stderr:
            console.print(result.stderr.rstrip())

        import json as _json

        drifted: list[str] = []
        healthy = True
        try:
            doctor_json = transport.download("/var/lib/loft-cli/doctor-result.json")
            doctor_data = _json.loads(doctor_json)
            healthy = doctor_data.get("healthy", False)
            drifted = [
                r.get("resource_id", r.get("id", "")) for r in doctor_data.get("drifted", []) if r
            ]
        except Exception:
            pass

        transport.close()

        if result.return_code != 0 or not healthy:
            return {"status": "drift", "drifted": drifted, "error": None}
        return {"status": "clean", "drifted": [], "error": None}

    except Exception as exc:
        return {"status": "error", "drifted": [], "error": str(exc)}


@app.command()
def doctor(
    spec: Path | None = typer.Argument(None, help="Path to YAML spec file (single-host mode)"),
    fleet: Path | None = typer.Option(None, "--fleet", help="Directory of spec files (fleet mode)"),
    selector: str | None = typer.Option(
        None, "--selector", help="Label selector to filter fleet specs (e.g. env=staging)"
    ),
    env_file: list[Path] | None = typer.Option(
        None, "--env-file", help="Load environment variables from .env file(s) (repeatable)"
    ),
    passthrough: bool = typer.Option(
        False,
        "--passthrough",
        help="Leave unresolved ${VAR} references unchanged instead of erroring",
    ),
    continue_on_error: bool = typer.Option(
        False,
        "--continue-on-error",
        help="In fleet mode: continue to next host on connection/execution error",
    ),
) -> None:
    """Report drift between desired spec and actual server state.

    Single-host mode:
        loft-cli doctor <spec.yaml>

    Fleet mode:
        loft-cli doctor --fleet <dir> [--selector <expr>]

    In fleet mode, all matched specs are checked and an aggregated summary
    table is printed.  Exit code 1 if any host is drifted or errored.
    """
    # ── Fleet mode ──────────────────────────────────────────────────
    if fleet is not None:
        _doctor_fleet(
            fleet_dir=fleet,
            selector_expr=selector or "",
            env_file=env_file,
            passthrough=passthrough,
            continue_on_error=continue_on_error,
        )
        return

    # ── Single-host mode (original behaviour) ───────────────────────
    if spec is None:
        console.print("[bold red]Error:[/bold red] Provide either a spec file or --fleet <dir>.")
        raise typer.Exit(1)

    from loft_cli.agent_installer import detect_agent
    from loft_cli.runtime.fabric_transport import FabricTransport

    try:
        parsed_spec, ctx, p, issues = _build_pipeline(
            spec, strict_env=not passthrough, env_file=env_file
        )
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1) from None

    if issues:
        _print_issues(issues, stop_on_error=True)

    # Connect to agent and run doctor
    try:
        login = parsed_spec.login
        key_path = (
            str(ctx.login_key_path) if ctx.login_key_path and ctx.login_key_path.exists() else None
        )
        transport = FabricTransport(
            host=parsed_spec.host.address,
            user=login.user,
            port=login.port,
            key_path=key_path,
            password=ctx.login_password,
        )

        agent_version = detect_agent(transport)
        if not agent_version:
            # Agent is not installed — attempt auto-install from local binary
            console.print(
                "[yellow]Agent not found on target server — attempting automatic install...[/yellow]"
            )
            from loft_cli.updater import update_agent

            installed = update_agent(transport, console=console)
            if not installed:
                console.print(
                    "[bold red]No agent installed on the target server and auto-install failed.[/bold red]\n"
                    "Install the agent first: loft-cli agent-update <host>"
                )
                transport.close()
                raise typer.Exit(1)
            agent_version = detect_agent(transport)
            if not agent_version:
                console.print(
                    "[bold red]Agent was installed but could not be detected.[/bold red]\n"
                    "Try running: loft-cli agent-update <host>"
                )
                transport.close()
                raise typer.Exit(1)

        from loft_cli import __version__
        from loft_cli.agent_installer import check_version_compatibility

        compatible, compat_msg = check_version_compatibility(__version__, agent_version)
        if not compatible:
            console.print(f"[bold red]Version mismatch:[/bold red] {compat_msg}")
            transport.close()
            raise typer.Exit(1)

        # Upload the current plan as the desired state
        from loft_cli_core.agent_paths import AGENT_BINARY_PATH, AGENT_DESIRED_DIR

        plan_json = p.model_dump_json(indent=2)
        plan_remote_path = f"{AGENT_DESIRED_DIR}/doctor-plan.json"
        transport.upload_content(plan_json, plan_remote_path, sudo=True)

        # Invoke agent doctor
        result = transport.run(
            f"{AGENT_BINARY_PATH} doctor {plan_remote_path}",
            sudo=True,
            warn=True,
        )

        # Print the agent's output
        if result.stdout:
            console.print(result.stdout.rstrip())
        if result.stderr:
            console.print(result.stderr.rstrip())

        # Download and display the doctor result
        import json as _json

        try:
            doctor_json = transport.download("/var/lib/loft-cli/doctor-result.json")
            doctor_data = _json.loads(doctor_json)
            healthy = doctor_data.get("healthy", False)
            if not healthy:
                console.print(
                    f"\n[bold yellow]Drift detected on {parsed_spec.host.address}.[/bold yellow]"
                    "\nRun 'loft-cli reconcile' to bring the server back to desired state."
                )
        except Exception:
            pass  # agent output already shown

        transport.close()

        if result.return_code != 0:
            raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]Doctor failed:[/bold red] {e}")
        raise typer.Exit(1) from None


def _doctor_fleet(
    fleet_dir: Path,
    selector_expr: str,
    env_file: list[Path] | None,
    passthrough: bool,
    continue_on_error: bool,
) -> None:
    """Fleet doctor: check drift on all specs matching the selector."""
    from loft_cli.local.selector import select_specs

    # Resolve matched specs
    try:
        if selector_expr:
            matches = select_specs(str(fleet_dir), selector_expr)
        else:
            # No selector: scan all specs in the directory
            from loft_cli.local.selector import _scan_all_specs

            matches = _scan_all_specs(str(fleet_dir))
    except ValueError as e:
        console.print(f"[bold red]Selector error:[/bold red] {e}")
        raise typer.Exit(1) from None

    label = selector_expr if selector_expr else "(all)"
    console.print(f"\n[bold]Fleet doctor:[/bold] {label} ({len(matches)} hosts)")

    # ── Per-spec doctor ──────────────────────────────────────────────
    rows: list[tuple[str, str, str, str]] = []  # (filepath, status, drifted, error)
    any_problem = False

    for filepath, parsed_spec in matches:
        # Build pipeline for this spec (re-parse with full pipeline for ctx/plan)
        try:
            spec_path = Path(filepath)
            _, ctx, p, issues = _build_pipeline(
                spec_path,
                strict_env=not passthrough,
                env_file=env_file,
            )
        except Exception as e:
            error_msg = str(e)[:80]
            rows.append((filepath, "error", "—", error_msg))
            any_problem = True
            if not continue_on_error:
                break
            continue

        console.print(f"  Checking [dim]{filepath}[/dim] ...")
        result = _run_doctor_on_spec(parsed_spec, ctx, p, console)

        if result["status"] == "clean":
            status_str = "[green]✓ clean[/green]"
            drifted_str = "—"
            error_str = "—"
        elif result["status"] == "drift":
            status_str = "[yellow]⚠ drift[/yellow]"
            drifted_str = ", ".join(result["drifted"]) or "unknown"
            error_str = "—"
            any_problem = True
        else:  # error
            status_str = "[red]✗ error[/red]"
            drifted_str = "—"
            error_str = (result["error"] or "")[:60]
            any_problem = True
            if not continue_on_error:
                rows.append((filepath, status_str, drifted_str, error_str))
                break

        rows.append((filepath, status_str, drifted_str, error_str))

    # ── Summary table ────────────────────────────────────────────────
    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
    table.add_column("Spec", min_width=30)
    table.add_column("Status", min_width=10)
    table.add_column("Drifted Resources", min_width=25)
    table.add_column("Error", min_width=20)

    for filepath, status_str, drifted_str, error_str in rows:
        table.add_row(filepath, status_str, drifted_str, error_str)

    console.print(table)

    # Counts
    clean_count = sum(1 for _, s, _, _ in rows if "clean" in s)
    drift_count = sum(1 for _, s, _, _ in rows if "drift" in s)
    error_count = sum(1 for _, s, _, _ in rows if "error" in s)
    console.print(
        f"\n{len(rows)} hosts checked: "
        f"[green]{clean_count} clean[/green], "
        f"[yellow]{drift_count} drifted[/yellow], "
        f"[red]{error_count} errored[/red]"
    )

    if any_problem:
        raise typer.Exit(1)


# ------------------------------------------------------------------ #
# reconcile
# ------------------------------------------------------------------ #


@app.command()
def reconcile(
    spec: Path = typer.Argument(..., help="Path to YAML spec file", exists=True),
    env_file: list[Path] | None = typer.Option(
        None, "--env-file", help="Load environment variables from .env file(s) (repeatable)"
    ),
    passthrough: bool = typer.Option(
        False,
        "--passthrough",
        help="Leave unresolved ${VAR} references unchanged instead of erroring",
    ),
) -> None:
    """Bring server back to desired state defined in the spec.

    This is equivalent to 'loft-cli apply' but communicates the intent:
    the server has drifted and needs to be reconciled. Only changed
    resources are re-applied (idempotent).
    """
    console.print("[bold]Reconciling server to desired state...[/bold]\n")

    # Reconcile is semantically identical to apply --mode agent
    # The agent's idempotent executor handles partial apply automatically.
    try:
        result = _build_pipeline(
            spec, ensure_keys=True, strict_env=not passthrough, env_file=env_file
        )
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1) from None

    specs_r, ctxs_r, plans_r, issues = result

    if issues:
        _print_issues(issues, stop_on_error=True)

    # Normalize to lists for uniform handling
    if isinstance(specs_r, list):
        spec_list = list(zip(specs_r, ctxs_r, plans_r, strict=True))
    else:
        spec_list = [(specs_r, ctxs_r, plans_r)]

    for parsed_spec, ctx, p in spec_list:
        _apply_single(parsed_spec, ctx, p, "agent", False, console)


# ------------------------------------------------------------------ #
# docs
# ------------------------------------------------------------------ #


@app.command()
def docs(
    spec: Path = typer.Argument(..., help="Path to YAML spec file", exists=True),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Output file (default: stdout)"
    ),
    mode: str = typer.Option("guide", "--mode", "-m", help="Output mode: guide or commands"),
    env_file: list[Path] | None = typer.Option(
        None, "--env-file", help="Load environment variables from .env file(s) (repeatable)"
    ),
    passthrough: bool = typer.Option(
        False,
        "--passthrough",
        help="Leave unresolved ${VAR} references unchanged instead of erroring",
    ),
) -> None:
    """Generate Markdown documentation from a spec's execution plan."""
    from loft_cli_core.plan.render_markdown import render_markdown

    try:
        result = _build_pipeline(spec, strict_env=not passthrough, env_file=env_file)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1) from None

    _, _, plans_r, issues = result

    if issues:
        _print_issues(issues, stop_on_error=True)

    plans_list = plans_r if isinstance(plans_r, list) else [plans_r]
    md = "\n\n---\n\n".join(render_markdown(p, mode=mode) for p in plans_list)

    if output:
        output.write_text(md, encoding="utf-8")
        console.print(f"[bold green]✓ Docs written to:[/bold green] {output}")
    else:
        print(md)


# ------------------------------------------------------------------ #
# apply
# ------------------------------------------------------------------ #


@app.command()
def apply(
    spec: Path | None = typer.Argument(None, help="Path to YAML spec file (single-spec mode)"),
    fleet: Path | None = typer.Option(None, "--fleet", help="Directory of spec files (fleet mode)"),
    selector: str | None = typer.Option(
        None, "--selector", help="Label selector to filter fleet specs (e.g. role=worker)"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be done without executing"
    ),
    env_file: list[Path] | None = typer.Option(
        None, "--env-file", help="Load environment variables from .env file(s) (repeatable)"
    ),
    passthrough: bool = typer.Option(
        False,
        "--passthrough",
        help="Leave unresolved ${VAR} references unchanged instead of erroring",
    ),
    mode: str = typer.Option(
        "auto",
        "--mode",
        help="Execution mode: 'auto' (detect agent), 'agent', or 'client' (Fabric)",
    ),
    continue_on_error: bool = typer.Option(
        False,
        "--continue-on-error",
        help="In fleet mode: continue to next host on failure instead of aborting",
    ),
) -> None:
    """Apply a spec to provision infrastructure.

    Single-spec mode:
        loft-cli apply <spec.yaml>

    Fleet mode:
        loft-cli apply --fleet <dir> [--selector <expr>] [--continue-on-error]
    """
    # ── Fleet mode ──────────────────────────────────────────────────
    if fleet is not None:
        _apply_fleet(
            fleet_dir=fleet,
            selector_expr=selector or "",
            env_file=env_file,
            passthrough=passthrough,
            mode=mode,
            dry_run=dry_run,
            continue_on_error=continue_on_error,
        )
        return

    # ── Single-spec mode (original behaviour) ───────────────────────
    if spec is None:
        console.print("[bold red]Error:[/bold red] Provide either a spec file or --fleet <dir>.")
        raise typer.Exit(1)

    try:
        result = _build_pipeline(
            spec, ensure_keys=True, strict_env=not passthrough, env_file=env_file
        )
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1) from None

    specs_r, ctxs_r, plans_r, issues = result

    if issues:
        _print_issues(issues, stop_on_error=True)

    # Normalize to lists for uniform handling
    if isinstance(specs_r, list):
        spec_list = list(zip(specs_r, ctxs_r, plans_r, strict=True))
    else:
        spec_list = [(specs_r, ctxs_r, plans_r)]

    for parsed_spec, ctx, p in spec_list:
        _apply_single(parsed_spec, ctx, p, mode, dry_run, console)


def _apply_fleet(
    fleet_dir: Path,
    selector_expr: str,
    env_file: list[Path] | None,
    passthrough: bool,
    mode: str,
    dry_run: bool,
    continue_on_error: bool,
) -> None:
    """Fleet apply: apply all specs matching the selector sequentially."""
    from loft_cli.local.selector import _scan_all_specs, select_specs

    try:
        if selector_expr:
            matches = select_specs(str(fleet_dir), selector_expr)
        else:
            matches = _scan_all_specs(str(fleet_dir))
    except ValueError as e:
        console.print(f"[bold red]Selector error:[/bold red] {e}")
        raise typer.Exit(1) from None

    label_str = f"selector: {selector_expr}" if selector_expr else "all"
    console.print(f"\n[bold]Fleet apply:[/bold] {len(matches)} hosts matched ({label_str})")

    succeeded: list[str] = []
    failed: list[tuple[str, str]] = []  # (filepath, error_message)

    for idx, (filepath, parsed_spec) in enumerate(matches, start=1):
        console.print(f"\n[{idx}/{len(matches)}] {filepath}")

        try:
            spec_path = Path(filepath)
            _, ctx, p, issues = _build_pipeline(
                spec_path,
                ensure_keys=True,
                strict_env=not passthrough,
                env_file=env_file,
            )
        except Exception as e:
            error_msg = str(e)
            console.print(f"  [bold red]Pipeline error:[/bold red] {error_msg}")
            failed.append((filepath, error_msg))
            if not continue_on_error:
                _print_fleet_apply_summary(succeeded, failed)
                raise typer.Exit(1) from None
            continue

        if issues:
            _print_issues(issues, stop_on_error=False)

        try:
            _apply_single(parsed_spec, ctx, p, mode, dry_run, console)
            succeeded.append(filepath)
        except SystemExit:
            error_msg = "apply failed (see above)"
            failed.append((filepath, error_msg))
            if not continue_on_error:
                _print_fleet_apply_summary(succeeded, failed)
                raise typer.Exit(1) from None
        except Exception as e:
            error_msg = str(e)
            console.print(f"  [bold red]Apply error:[/bold red] {error_msg}")
            failed.append((filepath, error_msg))
            if not continue_on_error:
                _print_fleet_apply_summary(succeeded, failed)
                raise typer.Exit(1) from None

    _print_fleet_apply_summary(succeeded, failed)
    if failed:
        raise typer.Exit(1)


def _print_fleet_apply_summary(succeeded: list[str], failed: list[tuple[str, str]]) -> None:
    """Print fleet apply done/failed summary."""
    console.print(f"\n[bold]Done:[/bold] {len(succeeded)} succeeded, {len(failed)} failed")
    if failed:
        for filepath, err in failed:
            console.print(f"  [red]Failed:[/red] {filepath} ({err})")


def _apply_single(parsed_spec, ctx, p, mode, dry_run, console) -> None:
    """Apply a single spec. Extracted to support multi-document iteration."""
    from loft_cli.local.inventory_db import InventoryDB
    from loft_cli.logs.writer import write_log
    from loft_cli.runtime.executor import Executor
    from loft_cli.runtime.fabric_transport import FabricTransport
    from loft_cli_core.registry import get_kind_hooks

    console.print(
        Panel(
            f"[bold]Applying:[/bold] {parsed_spec.meta.name}\n"
            f"[bold]Target:[/bold]  {parsed_spec.host.address}\n"
            f"[bold]Steps:[/bold]   {len(p.steps)}"
            + (" [yellow](DRY RUN)[/yellow]" if dry_run else ""),
            title="loft-cli apply",
            border_style="bright_blue",
        )
    )

    # Build transport (SSH session)
    transport = None
    if not dry_run:
        import socket

        def _tcp_reachable(host: str, port: int, timeout: float = 2.0) -> bool:
            try:
                with socket.create_connection((host, port), timeout=timeout):
                    return True
            except OSError:
                return False

        login = parsed_spec.login
        key_path = (
            str(ctx.login_key_path) if ctx.login_key_path and ctx.login_key_path.exists() else None
        )

        # For specs that declare ssh_port_fallback (e.g. bootstrap), if login.port is
        # unreachable try ssh.port as fallback. This allows clean re-runs after a
        # partial apply that already moved SSH to the new port.
        effective_port = login.port
        effective_user = login.user
        effective_key_path = key_path
        effective_password = ctx.login_password
        hooks = get_kind_hooks(parsed_spec.kind)
        if hooks.ssh_port_fallback and not _tcp_reachable(parsed_spec.host.address, login.port):
            fallback_port = parsed_spec.ssh.port
            if fallback_port != login.port and _tcp_reachable(
                parsed_spec.host.address, fallback_port
            ):
                console.print(
                    f"[yellow]⚠ login.port {login.port} unreachable — "
                    f"reconnecting on ssh.port {fallback_port}[/yellow]"
                )
                effective_port = fallback_port

                # When the port has already changed, the server may be fully
                # hardened (root login disabled, password auth disabled).  Try
                # the admin user with key auth on the fallback port first.
                admin_name = (
                    parsed_spec.admin_user.name if hasattr(parsed_spec, "admin_user") else None
                )
                admin_key = (
                    str(ctx.admin_key_path)
                    if ctx.admin_key_path and ctx.admin_key_path.exists()
                    else None
                )
                if admin_name and admin_key:
                    try:
                        probe = FabricTransport(
                            host=parsed_spec.host.address,
                            user=admin_name,
                            port=fallback_port,
                            key_path=admin_key,
                        )
                        if probe.test_connection():
                            console.print(
                                f"[yellow]⚠ Server already bootstrapped — "
                                f"using {admin_name}@{parsed_spec.host.address}:"
                                f"{fallback_port} with key auth[/yellow]"
                            )
                            effective_user = admin_name
                            effective_key_path = admin_key
                            effective_password = None
                        probe.close()
                    except Exception:
                        pass  # fall through to original credentials
            else:
                console.print(
                    f"[bold red]✗ Cannot reach {parsed_spec.host.address} "
                    f"on port {login.port} or {fallback_port} — "
                    f"check that the host is up and reachable.[/bold red]"
                )
                raise typer.Exit(1)

        transport = FabricTransport(
            host=parsed_spec.host.address,
            user=effective_user,
            port=effective_port,
            key_path=effective_key_path,
            password=effective_password,
        )

    # Determine execution mode (agent vs client)
    use_agent = False
    if transport and not dry_run:
        if mode == "agent":
            use_agent = True
        elif mode == "auto":
            from loft_cli.agent_installer import detect_agent

            agent_version = detect_agent(transport)
            if agent_version:
                from loft_cli import __version__
                from loft_cli.agent_installer import check_version_compatibility

                compatible, compat_msg = check_version_compatibility(__version__, agent_version)
                if not compatible:
                    console.print(f"[bold red]Version mismatch:[/bold red] {compat_msg}")
                    transport.close()
                    raise typer.Exit(1)
                console.print(
                    f"[dim]Agent detected (v{agent_version}) — using agent execution[/dim]"
                )
                use_agent = True
        # mode == "client" → use_agent stays False
        if mode == "client" or (mode == "auto" and not use_agent):
            console.print(
                "[dim]Using direct SSH execution "
                "(install loft-cli-agent on the target for agent mode)[/dim]"
            )

    # Build inventory DB
    inventory_db = None
    inv_cfg = parsed_spec.local.inventory
    if inv_cfg.enabled:
        inventory_db = InventoryDB(db_path=str(ctx.db_path))

    if use_agent:
        # Agent execution: upload plan, invoke agent, retrieve results
        from loft_cli.runtime.agent_transport import AgentTransport
        from loft_cli.runtime.executor import ApplyResult, StepResult

        agent_transport = AgentTransport(
            host=parsed_spec.host.address,
            user=effective_user,
            port=effective_port,
            key_path=effective_key_path,
            password=effective_password,
        )
        p.execution_mode = "agent"
        agent_result = agent_transport.apply_plan(p)

        # Print agent step results
        icons = {"success": "✓", "failed": "✗", "skipped": "○", "unchanged": "≡"}
        colors = {"success": "green", "failed": "red", "skipped": "dim", "unchanged": "blue"}
        for sr in agent_result.step_results:
            icon = icons.get(sr.status, "?")
            color = colors.get(sr.status, "white")
            duration = f"{sr.duration_seconds:.1f}s" if sr.duration_seconds else ""
            console.print(
                f"  [{color}]{icon}[/{color}] [{sr.step_index:>2}] {sr.step_id[:50]}"
                + (f" [{duration}]" if duration else ""),
            )
            if sr.status == "failed" and sr.error:
                console.print(f"     [red]{sr.error[:120]}[/red]")

        console.print(
            f"\n[dim]Agent: {agent_result.applied_count} applied, "
            f"{agent_result.unchanged_count} unchanged[/dim]"
        )

        # Run local steps via the regular executor
        local_executor = Executor(
            plan=p,
            transport=transport,
            inventory_db=inventory_db,
            ctx=ctx,
            spec=parsed_spec,
            console=console,
        )
        # Only execute LOCAL-scoped steps
        local_result = local_executor.apply(dry_run=dry_run)

        # Merge into a single ApplyResult for logging
        result = ApplyResult(
            plan=p,
            step_results=[
                StepResult(
                    step_index=sr.step_index,
                    step_id=sr.step_id,
                    scope=sr.scope,
                    status="success" if sr.status in ("success", "unchanged") else sr.status,
                    output=sr.output,
                    error=sr.error,
                    duration_seconds=sr.duration_seconds,
                )
                for sr in agent_result.step_results
            ]
            + local_result.step_results,
            status=agent_result.status if agent_result.status == "failed" else local_result.status,
            aborted_at=agent_result.aborted_at,
            started_at=agent_result.started_at,
            finished_at=local_result.finished_at,
        )
        agent_transport.close()
    else:
        # Client execution: direct SSH via Fabric (original path)
        executor = Executor(
            plan=p,
            transport=transport,
            inventory_db=inventory_db,
            ctx=ctx,
            spec=parsed_spec,
            console=console,
            effective_port=(effective_port if transport and effective_port != login.port else None),
        )
        result = executor.apply(dry_run=dry_run)

    # Post-apply: record inventory via the kind's registered hook.
    if not dry_run and inventory_db and "success" in result.status:
        try:
            record_fn = get_kind_hooks(parsed_spec.kind).on_inventory_record
            if record_fn is not None:
                record_fn(inventory_db, parsed_spec, result)
        except Exception as e:
            console.print(f"[yellow]⚠ Inventory update failed: {e}[/yellow]")
        finally:
            inventory_db.close()

    # Write execution log
    if not dry_run:
        try:
            log_path = write_log(result)
            console.print(f"\n[dim]Run log: {log_path}[/dim]")
        except Exception as e:
            console.print(f"[yellow]⚠ Log write failed: {e}[/yellow]")

    # Close transport
    if transport:
        transport.close()

    # Summary
    status_color = {
        "success": "green",
        "success_with_local_warnings": "yellow",
        "failed": "red",
    }.get(result.status, "white")

    console.print(f"\n[bold {status_color}]Status: {result.status}[/bold {status_color}]")

    if result.status == "failed":
        raise typer.Exit(1)


# ------------------------------------------------------------------ #
# rotate-secret
# ------------------------------------------------------------------ #


@app.command(name="rotate-secret")
def rotate_secret_cmd(
    spec: Path = typer.Argument(..., help="Path to YAML spec file", exists=True),
    secret: str = typer.Option(..., "--secret", help="Environment variable name to rotate"),
    value: str | None = typer.Option(
        None, "--value", help="New secret value (generated if omitted)"
    ),
    env_file: list[Path] | None = typer.Option(
        None, "--env-file", help="Load environment variables from .env file(s) (repeatable)"
    ),
    passthrough: bool = typer.Option(
        False,
        "--passthrough",
        help="Leave unresolved ${VAR} references unchanged instead of erroring",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would change without applying"
    ),
) -> None:
    """Rotate a secret (password_env) and re-apply affected steps."""
    from loft_cli.compiler.parser import parse
    from loft_cli.runtime.secret_rotation import rotate_secret

    console.print(f"[bold]Rotating secret:[/bold] {secret}")

    # Parse the spec first to find references
    try:
        parsed = parse(spec, strict_env=not passthrough, env_files=env_file)
    except Exception as e:
        console.print(f"[bold red]Parse error:[/bold red] {e}")
        raise typer.Exit(1) from None

    specs_list = parsed if isinstance(parsed, list) else [parsed]

    # Find and rotate the secret
    all_refs = []
    for s in specs_list:
        result = rotate_secret(s, secret, value)
        all_refs.extend(result.refs_found)

    if not all_refs:
        console.print(f"[bold red]No references to '{secret}' found in spec.[/bold red]")
        raise typer.Exit(1)

    console.print(f"  Found {len(all_refs)} reference(s):")
    for ref in all_refs:
        console.print(f"    • {ref.field_path} (kind: {ref.kind})")

    generated = value is None
    if generated:
        console.print("  [dim]Generated new password (32 chars)[/dim]")

    if dry_run:
        console.print("\n[yellow]Dry run — no changes applied.[/yellow]")
        return

    # Re-run the full pipeline with the new secret in the environment
    console.print("\n[bold]Re-applying with rotated secret...[/bold]")
    try:
        pipeline_result = _build_pipeline(
            spec, ensure_keys=True, strict_env=not passthrough, env_file=env_file
        )
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1) from None

    specs_r, ctxs_r, plans_r, issues = pipeline_result

    if issues:
        _print_issues(issues, stop_on_error=True)

    if isinstance(specs_r, list):
        spec_list = list(zip(specs_r, ctxs_r, plans_r, strict=True))
    else:
        spec_list = [(specs_r, ctxs_r, plans_r)]

    for parsed_spec, ctx, p in spec_list:
        _apply_single(parsed_spec, ctx, p, "agent", False, console)

    console.print(f"\n[bold green]Secret '{secret}' rotated successfully.[/bold green]")


# ------------------------------------------------------------------ #
# tunnel up | down | status
# ------------------------------------------------------------------ #


@tunnel_app.command("up")
def tunnel_up_cmd(
    host: str = typer.Argument(..., help="Host name or provider/host (e.g., hetzner/dev-vps)"),
    env_file: list[Path] | None = typer.Option(
        None, "--env-file", help="Load environment variables from .env file(s)"
    ),
) -> None:
    """Bring up the WireGuard tunnel for a host."""
    from loft_cli.local.tunnel import tunnel_up

    provider, host_name = _parse_identifier(host)
    console.print(f"[bold]Bringing up WireGuard tunnel for {host}...[/bold]")
    ok, msg = tunnel_up(host_name, provider)
    if ok:
        console.print(f"[bold green]{msg}[/bold green]")
    else:
        console.print(f"[bold red]{msg}[/bold red]")
        raise typer.Exit(1)


@tunnel_app.command("down")
def tunnel_down_cmd(
    host: str = typer.Argument(..., help="Host name or provider/host (e.g., hetzner/dev-vps)"),
    env_file: list[Path] | None = typer.Option(
        None, "--env-file", help="Load environment variables from .env file(s)"
    ),
) -> None:
    """Tear down the WireGuard tunnel for a host."""
    from loft_cli.local.tunnel import tunnel_down

    provider, host_name = _parse_identifier(host)
    console.print(f"[bold]Tearing down WireGuard tunnel for {host}...[/bold]")
    ok, msg = tunnel_down(host_name, provider)
    if ok:
        console.print(f"[bold green]{msg}[/bold green]")
    else:
        console.print(f"[bold red]{msg}[/bold red]")
        raise typer.Exit(1)


@tunnel_app.command("status")
def tunnel_status_cmd() -> None:
    """List all hosts with WireGuard tunnel status."""
    from loft_cli.local.tunnel import tunnel_status

    hosts = tunnel_status()
    if not hosts:
        console.print("[dim]No WireGuard hosts found.[/dim]")
        return

    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
    table.add_column("Host", min_width=15)
    table.add_column("Provider", min_width=10)
    table.add_column("Interface", min_width=12)
    table.add_column("VPN IP", min_width=12)
    table.add_column("Endpoint", min_width=20)
    table.add_column("Status", min_width=8)
    table.add_column("Deployed")

    for h in hosts:
        status_text = (
            Text("active", style="green") if h["active"] else Text("inactive", style="dim")
        )
        table.add_row(
            h["host_name"],
            h.get("provider", "") or "-",
            h["interface"],
            h["vpn_ip"],
            h["endpoint"],
            status_text,
            h["deployed_at"][:19] if h["deployed_at"] else "",
        )
    console.print(table)


# ------------------------------------------------------------------ #
# remove <host>
# ------------------------------------------------------------------ #


@app.command()
def remove(
    host: str = typer.Argument(
        ...,
        help="Host name or provider/host format (e.g., hetzner/dev-vps) to remove all local state for",
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
) -> None:
    """Remove all local loft-cli state for a decommissioned machine.

    Tears down any active WireGuard tunnel, removes WG state, SSH config,
    SSH keys, and marks the inventory record as decommissioned.

    Use provider/host format to remove provider-scoped state:
        loft remove hetzner/dev-vps

    Or legacy single-level format:
        loft remove dev-vps
    """
    from loft_cli.local.remove import remove_host

    if not force:
        confirm = typer.confirm(f"Remove all local state for '{host}'?")
        if not confirm:
            console.print("[dim]Cancelled.[/dim]")
            raise typer.Exit(0)

    results = remove_host(host, console=console)

    if any(r["status"] == "error" for r in results):
        console.print(f"\n[bold yellow]Host '{host}' removed with warnings.[/bold yellow]")
    else:
        console.print(f"\n[bold green]Host '{host}' removed successfully.[/bold green]")


# ------------------------------------------------------------------ #
# inspect run <run-id>
# ------------------------------------------------------------------ #


@inspect_app.command("run")
def inspect_run(
    run_id: str = typer.Argument(..., help="Run ID (or prefix) to inspect"),
) -> None:
    """Show details of a past apply run."""
    from loft_cli.logs.reader import find_log, read_log

    log_path = find_log(run_id)
    if not log_path:
        from loft_cli_core.registry.local_paths import get_local_paths

        log_dir = get_local_paths().log_dir
        console.print(f"[red]Run '{run_id}' not found in {log_dir}[/red]")
        raise typer.Exit(1)

    data = read_log(log_path)

    console.print(
        Panel(
            f"[bold]Spec:[/bold]   {data.get('spec_name')} ({data.get('spec_kind')})\n"
            f"[bold]Target:[/bold] {data.get('target_host')}\n"
            f"[bold]Status:[/bold] {data.get('status')}\n"
            f"[bold]Started:[/bold] {data.get('started_at')}\n"
            f"[bold]Finished:[/bold] {data.get('finished_at')}",
            title=f"Run: {data.get('run_id')}",
        )
    )

    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
    table.add_column("#", width=4)
    table.add_column("Step", min_width=30)
    table.add_column("Scope", width=8)
    table.add_column("Status", width=10)
    table.add_column("Duration", width=10)

    for step in data.get("steps", []):
        status = step["status"]
        color = {"success": "green", "failed": "red", "skipped": "dim"}.get(status, "white")
        table.add_row(
            str(step["index"]),
            step["id"],
            step["scope"],
            Text(status, style=color),
            f"{step['duration_seconds']:.1f}s",
        )

    console.print(table)


# ------------------------------------------------------------------ #
# inventory list | show
# ------------------------------------------------------------------ #


def _get_db() -> InventoryDB:
    from loft_cli.local.inventory_db import InventoryDB
    from loft_cli_core.registry.local_paths import get_local_paths

    # Explicit LOFT_CLI_DB_PATH takes priority (backward compat),
    # then fall back to get_local_paths() which respects LOFT_CLI_STATE_DIR.
    db_path = os.environ.get("LOFT_CLI_DB_PATH") or str(get_local_paths().inventory_db_path)
    db = InventoryDB(db_path=db_path)
    db.open()
    return db


@inventory_app.command("list")
def inventory_list() -> None:
    """List all provisioned servers from local inventory."""
    db = _get_db()
    try:
        servers = db.list_servers()
    finally:
        db.close()

    if not servers:
        console.print("[dim]No servers in inventory.[/dim]")
        return

    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
    table.add_column("Name", min_width=20)
    table.add_column("Address", min_width=15)
    table.add_column("Status", min_width=15)
    table.add_column("SSH", min_width=25)
    table.add_column("WireGuard")

    for s in servers:
        ssh_info = f"{s.get('ssh_user', '')}@{s.get('ssh_alias', s.get('name', ''))}:{s.get('ssh_port', '')}"
        wg = "yes" if s.get("wireguard_enabled") else "no"
        status_color = "green" if s.get("bootstrap_status") == "bootstrapped" else "yellow"
        table.add_row(
            s.get("name", ""),
            s.get("address", ""),
            Text(s.get("bootstrap_status", ""), style=status_color),
            ssh_info,
            wg,
        )
    console.print(table)


@inventory_app.command("show")
def inventory_show(
    server_id: str = typer.Argument(..., help="Server name or ID"),
) -> None:
    """Show details of a specific server from local inventory."""
    from loft_cli.local.inventory import show_server

    db = _get_db()
    try:
        data = show_server(db, server_id)
    finally:
        db.close()

    if data is None:
        console.print(f"[red]Server '{server_id}' not found in inventory.[/red]")
        raise typer.Exit(1)

    lines = []
    for k, v in data.items():
        if k == "services":
            continue
        lines.append(f"[bold]{k}:[/bold] {v}")
    console.print(Panel("\n".join(lines), title=f"Server: {server_id}"))

    services = data.get("services", [])
    if services:
        console.print("\n[bold]Services:[/bold]")
        for svc in services:
            console.print(
                f"  • {svc.get('service_type')}: {svc.get('service_name')} [{svc.get('status')}]"
            )
    else:
        console.print("[dim]No services recorded.[/dim]")


# ------------------------------------------------------------------ #
# logs
# ------------------------------------------------------------------ #


@app.command()
def logs(
    host: str | None = typer.Argument(None, help="Filter logs by target host (partial match)"),
    limit: int = typer.Option(20, "--limit", "-n", help="Maximum number of log entries to show"),
    run_id: str | None = typer.Option(None, "--run", help="Show a specific run by ID or prefix"),
) -> None:
    """List recent apply runs, optionally filtered by host.

    Pass --run <id> to show full step details for a specific run.
    """
    from loft_cli.logs.reader import find_log, list_logs, read_log

    if run_id:
        # Show detail for a specific run
        log_path = find_log(run_id)
        if not log_path:
            from loft_cli_core.registry.local_paths import get_local_paths

            log_dir = get_local_paths().log_dir
            console.print(f"[red]Run '{run_id}' not found in {log_dir}[/red]")
            raise typer.Exit(1)

        data = read_log(log_path)
        console.print(
            Panel(
                f"[bold]Spec:[/bold]    {data.get('spec_name')} ({data.get('spec_kind')})\n"
                f"[bold]Target:[/bold]  {data.get('target_host')}\n"
                f"[bold]Status:[/bold]  {data.get('status')}\n"
                f"[bold]Started:[/bold] {data.get('started_at')}\n"
                f"[bold]Finished:[/bold] {data.get('finished_at')}",
                title=f"Run: {data.get('run_id')}",
            )
        )

        table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
        table.add_column("#", width=4)
        table.add_column("Step", min_width=30)
        table.add_column("Scope", width=8)
        table.add_column("Status", width=10)
        table.add_column("Duration", width=10)

        for step in data.get("steps", []):
            status = step["status"]
            color = {"success": "green", "failed": "red", "skipped": "dim"}.get(status, "white")
            table.add_row(
                str(step["index"]),
                step["id"],
                step["scope"],
                Text(status, style=color),
                f"{step['duration_seconds']:.1f}s",
            )

        console.print(table)
        return

    # List recent runs
    all_logs = list_logs()

    if host:
        all_logs = [
            entry for entry in all_logs if host.lower() in (entry.get("target_host") or "").lower()
        ]

    all_logs = all_logs[:limit]

    if not all_logs:
        console.print("[dim]No apply runs found.[/dim]")
        return

    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
    table.add_column("Run ID", min_width=20)
    table.add_column("Spec", min_width=20)
    table.add_column("Host", min_width=15)
    table.add_column("Status", width=12)
    table.add_column("Started", min_width=20)

    for entry in all_logs:
        status = entry.get("status", "")
        color = {
            "success": "green",
            "success_with_local_warnings": "yellow",
            "failed": "red",
        }.get(status, "white")
        table.add_row(
            entry.get("run_id", ""),
            entry.get("spec_name", ""),
            entry.get("target_host", ""),
            Text(status, style=color),
            (entry.get("started_at") or "")[:19],
        )

    console.print(table)


if __name__ == "__main__":
    app()


# ------------------------------------------------------------------ #
# catalog list | show | export
# ------------------------------------------------------------------ #


@catalog_app.command("list")
def catalog_list() -> None:
    """List all registered spec kinds with their descriptions."""
    from loft_cli_core.registry.catalog import list_catalog_entries

    entries = list_catalog_entries()
    if not entries:
        console.print("[dim]No catalog entries registered.[/dim]")
        return

    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
    table.add_column("Kind", min_width=20)
    table.add_column("Description")

    for entry in entries:
        table.add_row(entry.kind, entry.description)

    console.print(table)


@catalog_app.command("show")
def catalog_show(
    kind: str = typer.Argument(..., help="Spec kind to show details for (e.g. 'bootstrap')"),
) -> None:
    """Show detailed field information for a single spec kind."""
    from loft_cli_core.registry.catalog import get_catalog_entry

    entry = get_catalog_entry(kind)
    if entry is None:
        console.print(f"[bold red]Unknown kind:[/bold red] '{kind}'")
        console.print("[dim]Run 'loft-cli catalog list' to see all available kinds.[/dim]")
        raise typer.Exit(1)

    console.print(f"\n[bold]Kind:[/bold] {entry.kind}")
    console.print(entry.description)

    if entry.fields:
        console.print("\n[bold]Fields:[/bold]")
        for field in entry.fields:
            required_tag = (
                "[red](required)[/red]" if field.get("required") else "[dim](optional)[/dim]"
            )
            name = field.get("name", "")
            type_str = field.get("type", "")
            desc = field.get("description", "")
            console.print(f"  [cyan]{name:<30}[/cyan] {type_str:<12} {required_tag}  {desc}")
    else:
        console.print("\n[dim]No field metadata available.[/dim]")

    if entry.outputs:
        console.print("\n[bold]Outputs:[/bold]")
        for output in entry.outputs:
            console.print(f"  [green]{output.name}[/green]")
            console.print(f"    {output.description}")
            if output.example:
                console.print(f"    [dim]Example: {output.example}[/dim]")


@catalog_app.command("export")
def catalog_export() -> None:
    """Serialize all catalog entries to JSON and print to stdout."""
    import json

    from loft_cli_core.registry.catalog import list_catalog_entries

    entries = list_catalog_entries()

    data = {
        "kinds": [
            {
                "kind": entry.kind,
                "description": entry.description,
                "fields": entry.fields,
                "outputs": [
                    {
                        "name": o.name,
                        "description": o.description,
                        "example": o.example,
                    }
                    for o in entry.outputs
                ],
            }
            for entry in entries
        ]
    }

    print(json.dumps(data, indent=2))


# ------------------------------------------------------------------ #
# prep
# ------------------------------------------------------------------ #


@app.command(name="prep")
def prep(
    spec: Path = typer.Argument(..., help="Path to YAML spec file", exists=True),
    env_file: list[Path] | None = typer.Option(
        None, "--env-file", help="Load environment variables from .env file(s) (repeatable)"
    ),
    check_connection: bool = typer.Option(
        False, "--check-connection", help="Verify SSH connectivity after key generation"
    ),
) -> None:
    """Prepare a host for bootstrapping: generate SSH keys, display public key."""
    from loft_cli.commands.prep import main as prep_main

    prep_main(spec, env_file, check_connection)
