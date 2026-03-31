"""loft prep — generate SSH keys and optionally verify connectivity."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import typer

if TYPE_CHECKING:
    from rich.console import Console

app = typer.Typer(help="Prepare host for bootstrapping: generate SSH keys, verify connectivity.")


@app.command()
def main(
    spec: Path = typer.Argument(..., help="Path to YAML spec file", exists=True),
    env_file: list[Path] | None = typer.Option(
        None, "--env-file", help="Load environment variables from .env file(s) (repeatable)"
    ),
    check_connection: bool = typer.Option(
        False, "--check-connection", help="Verify SSH connectivity after key generation"
    ),
) -> None:
    """Prepare a host for bootstrapping.

    This command:
    1. Generates an SSH keypair at ~/.loft-cli/keys/{provider}/{host}/id_ed25519
    2. Displays the public key for copy-paste to your cloud provider
    3. Optionally verifies SSH connectivity

    Example:
        loft prep 01-bootstrap/bootstrap.yaml --env-file .env
    """
    from loft_cli.compiler.parser import parse
    from loft_cli_core.specs.validators import validate_spec, has_errors
    from loft_cli_core.registry import load_addons

    load_addons()

    console = typer.get_autoesuggest()
    if console is None:
        from rich.console import Console

        console = Console()

    parsed = parse(spec, strict_env=True, env_files=env_file)

    if isinstance(parsed, list):
        console.print("[red]Multi-document specs not supported for prep.[/red]")
        raise typer.Exit(1)

    spec = parsed

    if spec.kind != "bootstrap":
        console.print(f"[red]Only bootstrap specs supported, got kind: {spec.kind}[/red]")
        raise typer.Exit(1)

    issues = validate_spec(spec)
    error_issues = [i for i in issues if i.severity == "error"]
    if error_issues:
        console.print("[red]Validation errors:[/red]")
        for issue in error_issues:
            console.print(f"  [red]{issue}[/red]")
        raise typer.Exit(1)

    warning_issues = [i for i in issues if i.severity == "warning"]
    if warning_issues:
        console.print("[yellow]Validation warnings:[/yellow]")
        for issue in warning_issues:
            console.print(f"  [yellow]{issue}[/yellow]")
        console.print()

    provider = getattr(spec.host, "provider", "") or ""
    host_name = spec.host.name

    if not provider:
        console.print("[red]host.provider is required for key generation.[/red]")
        raise typer.Exit(1)

    from loft_cli.local.keys import ensure_ssh_keypair

    try:
        priv_key_path = ensure_ssh_keypair(provider, host_name, console=console)
    except Exception as e:
        console.print(f"[red]Failed to generate SSH keypair: {e}[/red]")
        raise typer.Exit(1)

    pub_key_path = priv_key_path.with_suffix(".pub")
    if not pub_key_path.exists():
        console.print("[red]Public key not found after generation.[/red]")
        raise typer.Exit(1)

    pub_key_content = pub_key_path.read_text().strip()

    console.print()
    console.print(f"[green]SSH keypair ready:[/green] {provider}/{host_name}")
    console.print(f"Path: [dim]{priv_key_path}[/dim]")
    console.print()

    console.print("[bold]Public key (copy to your cloud provider):[/bold]")
    console.print("─" * 48)
    console.print(f"[cyan]{pub_key_content}[/cyan]")
    console.print("─" * 48)
    console.print()

    console.print("[bold]Next steps:[/bold]")
    console.print("  1. Add this public key in your cloud provider console → SSH Keys")
    console.print("  2. Create or rebuild the server with this key")
    if check_connection:
        console.print("  3. Verify: loft prep ... --check-connection")
    console.print("  4. Bootstrap: loft apply ...")
    console.print()

    if check_connection:
        _verify_connection(spec, console)


def _verify_connection(spec, console: "Console") -> None:
    """Verify SSH connectivity to the host."""
    from loft_cli.local.keys import ssh_key_dir

    provider = getattr(spec.host, "provider", "") or ""
    host_name = spec.host.name

    key_path = ssh_key_dir(provider, host_name) / "id_ed25519"

    if not key_path.exists():
        console.print("[red]SSH key not found.[/red]")
        raise typer.Exit(1)

    perms = oct(key_path.stat().st_mode)[-3:]
    if perms != "600":
        console.print(f"[yellow]Warning: key permissions are {perms}, should be 600[/yellow]")

    host = spec.host.address
    port = spec.login.port
    user = spec.login.user

    console.print(f"\n[bold]Verifying SSH connectivity...[/bold]")
    console.print(f"  Host: {host}:{port}")
    console.print(f"  User: {user}")
    console.print(f"  Key: {key_path}")

    try:
        result = subprocess.run(
            [
                "ssh",
                "-o",
                "StrictHostKeyChecking=no",
                "-o",
                "UserKnownHostsFile=/dev/null",
                "-o",
                "BatchMode=yes",
                "-o",
                "ConnectTimeout=10",
                "-i",
                str(key_path),
                "-p",
                str(port),
                f"{user}@{host}",
                "echo 'SSH connection successful'",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )

        if result.returncode == 0:
            console.print(f"\n[green]✓ SSH connection successful![/green]")
            console.print(f"  Response: {result.stdout.strip()}")
        else:
            console.print(f"\n[red]✗ SSH connection failed[/red]")
            if result.stderr:
                console.print(f"  Error: {result.stderr.strip()}")
            raise typer.Exit(1)

    except subprocess.TimeoutExpired:
        console.print(f"\n[red]✗ Connection timed out (15s)[/red]")
        raise typer.Exit(1)
    except FileNotFoundError:
        console.print(f"\n[red]✗ SSH command not found[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"\n[red]✗ Connection error: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
