"""Tests for the CLI interface."""
import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

# Import will fail initially, that's expected in TDD
from provision.cli import app

runner = CliRunner()


def test_cli_help():
    """Test CLI help command."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "provisioning tool" in result.stdout.lower()
    # Look for options instead of command name
    assert "--dry-run" in result.stdout.lower()


@patch('provision.utils.is_root')
@patch('provision.steps.provision_system')
def test_setup_command_default(mock_provision, mock_is_root):
    """Test setup command with default options."""
    mock_is_root.return_value = True
    
    result = runner.invoke(app, [])
    
    assert result.exit_code == 0
    mock_provision.assert_called_once_with(False, False)
    assert "✅" in result.stdout


@patch('provision.utils.is_root')
def test_setup_requires_root_without_user_only(mock_is_root):
    """Test setup command fails when not root and --user-only not specified."""
    mock_is_root.return_value = False
    
    result = runner.invoke(app, [])
    
    assert result.exit_code == 1
    assert "root" in result.stdout.lower()


@patch('provision.utils.is_root')
@patch('provision.steps.provision_system')
def test_setup_user_only_no_root_required(mock_provision, mock_is_root):
    """Test setup with --user-only doesn't require root."""
    mock_is_root.return_value = False
    
    result = runner.invoke(app, ["--user-only"])
    
    assert result.exit_code == 0
    mock_provision.assert_called_once_with(False, True)


@patch('provision.utils.is_root')
@patch('provision.steps.provision_system')
def test_setup_dry_run(mock_provision, mock_is_root):
    """Test setup with --dry-run option."""
    mock_is_root.return_value = True
    
    result = runner.invoke(app, ["--dry-run"])
    
    assert result.exit_code == 0
    mock_provision.assert_called_once_with(True, False)


@patch('provision.utils.setup_logging')
@patch('provision.utils.is_root')
@patch('provision.steps.provision_system')
def test_setup_verbose(mock_provision, mock_is_root, mock_logging):
    """Test setup with --verbose option."""
    mock_is_root.return_value = True
    
    result = runner.invoke(app, ["--verbose"])
    
    assert result.exit_code == 0
    mock_logging.assert_called_once_with(True)
    mock_provision.assert_called_once_with(False, False)