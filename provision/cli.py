"""CLI interface for the mm (macOS management) tool."""
import subprocess
import typer
from . import utils
from . import steps
from . import macos

state: dict = {}

app = typer.Typer(
    name="mm",
    help="macOS management CLI.",
    add_completion=False,
)


@app.callback()
def main(
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview changes without applying them"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
):
    """Global options for mm."""
    state["dry_run"] = dry_run
    state["verbose"] = verbose
    utils.setup_logging(verbose)


@app.command()
def provision(
    user_only: bool = typer.Option(False, "--user-only", help="Skip operations requiring root"),
):
    """Run the full provisioning workflow."""
    dry_run = state["dry_run"]

    if not user_only and not dry_run:
        subprocess.run(["sudo", "-v"], check=True)

    steps.provision_system(dry_run, user_only)
    typer.echo("Provisioning complete!")


update_app = typer.Typer(
    name="update",
    help="Update individual components.",
)
app.add_typer(update_app)


@update_app.command()
def tailscale():
    """Update Tailscale from source."""
    macos.install_tailscale(dry_run=state["dry_run"])


runner_app = typer.Typer(
    name="runner",
    help="Manage GitHub Actions runners.",
)
app.add_typer(runner_app)


@runner_app.command()
def install():
    """Install GitHub Actions runners as LaunchDaemons."""
    dry_run = state["dry_run"]

    if not dry_run:
        subprocess.run(["sudo", "-v"], check=True)

    macos.install_runner_daemons(dry_run=dry_run)


if __name__ == "__main__":
    app()
