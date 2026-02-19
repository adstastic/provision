"""Tests for the CLI interface."""
from typer.testing import CliRunner
from unittest.mock import patch

from provision.cli import app, state

runner = CliRunner()


def test_help_shows_subcommands():
    """mm --help lists provision and update subcommands."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "provision" in result.stdout
    assert "update" in result.stdout


def test_provision_help_shows_user_only():
    """mm provision --help shows --user-only option."""
    result = runner.invoke(app, ["provision", "--help"])
    assert result.exit_code == 0
    assert "--user-only" in result.stdout


def test_update_help_shows_tailscale():
    """mm update --help shows tailscale subcommand."""
    result = runner.invoke(app, ["update", "--help"])
    assert result.exit_code == 0
    assert "tailscale" in result.stdout


@patch("provision.cli.subprocess.run")
@patch("provision.steps.provision_system")
def test_provision_default(mock_provision, mock_subprocess):
    """mm provision caches sudo and runs full workflow."""
    result = runner.invoke(app, ["provision"])

    assert result.exit_code == 0
    mock_subprocess.assert_called_once_with(["sudo", "-v"], check=True)
    mock_provision.assert_called_once_with(False, False)
    assert "Provisioning complete!" in result.stdout


@patch("provision.steps.provision_system")
def test_provision_user_only(mock_provision):
    """mm provision --user-only skips sudo caching."""
    result = runner.invoke(app, ["provision", "--user-only"])

    assert result.exit_code == 0
    mock_provision.assert_called_once_with(False, True)


@patch("provision.steps.provision_system")
def test_provision_dry_run(mock_provision):
    """mm --dry-run provision skips sudo and passes dry_run."""
    result = runner.invoke(app, ["--dry-run", "provision"])

    assert result.exit_code == 0
    mock_provision.assert_called_once_with(True, False)


@patch("provision.cli.subprocess.run")
@patch("provision.steps.provision_system")
def test_provision_verbose(mock_provision, mock_subprocess):
    """mm --verbose provision enables verbose logging."""
    with patch("provision.utils.setup_logging") as mock_logging:
        result = runner.invoke(app, ["--verbose", "provision"])

    assert result.exit_code == 0
    mock_logging.assert_called_once_with(True)
    mock_provision.assert_called_once_with(False, False)


@patch("provision.macos.install_tailscale")
def test_update_tailscale(mock_install):
    """mm update tailscale calls install_tailscale."""
    result = runner.invoke(app, ["update", "tailscale"])

    assert result.exit_code == 0
    mock_install.assert_called_once_with(dry_run=False)


@patch("provision.macos.install_tailscale")
def test_update_tailscale_dry_run(mock_install):
    """mm --dry-run update tailscale passes dry_run."""
    result = runner.invoke(app, ["--dry-run", "update", "tailscale"])

    assert result.exit_code == 0
    mock_install.assert_called_once_with(dry_run=True)


def test_help_shows_runner():
    """mm --help lists runner subcommand."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "runner" in result.stdout


def test_runner_help_shows_install():
    """mm runner --help shows install subcommand."""
    result = runner.invoke(app, ["runner", "--help"])
    assert result.exit_code == 0
    assert "install" in result.stdout


@patch("provision.cli.subprocess.run")
@patch("provision.macos.install_runner_daemons")
def test_runner_install(mock_install, mock_subprocess):
    """mm runner install caches sudo and calls install_runner_daemons."""
    result = runner.invoke(app, ["runner", "install"])

    assert result.exit_code == 0
    mock_subprocess.assert_called_once_with(["sudo", "-v"], check=True)
    mock_install.assert_called_once_with(dry_run=False)


@patch("provision.macos.install_runner_daemons")
def test_runner_install_dry_run(mock_install):
    """mm --dry-run runner install skips sudo and passes dry_run."""
    result = runner.invoke(app, ["--dry-run", "runner", "install"])

    assert result.exit_code == 0
    mock_install.assert_called_once_with(dry_run=True)
