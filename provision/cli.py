"""CLI interface for the provisioning tool."""
import typer
from . import utils
from . import steps


def setup(
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview changes without applying them"),
    user_only: bool = typer.Option(False, "--user-only", help="Skip operations requiring root"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
):
    """Setup and harden system for headless server operation."""
    utils.setup_logging(verbose)
    
    # Check root if needed
    if not user_only and not utils.is_root():
        typer.echo("❗ System operations require root. Run with sudo or use --user-only")
        raise typer.Exit(1)
    
    steps.provision_system(dry_run, user_only)
    typer.echo("✅ Provisioning complete!")


app = typer.Typer(
    name="provision",
    help="A clean, modular system provisioning tool.",
    add_completion=False,
    invoke_without_command=True,
    callback=setup,
)


if __name__ == "__main__":
    app()