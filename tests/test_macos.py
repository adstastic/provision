"""Tests for macOS-specific provisioning functions."""
import pytest
from unittest.mock import patch, MagicMock, call
import sh
from pathlib import Path

from provision.macos import check_homebrew, install_homebrew, install_brewfile_packages


class TestHomebrewCheck:
    """Tests for Homebrew detection."""
    
    @patch('provision.macos.command_exists')
    def test_check_homebrew_installed(self, mock_command_exists):
        """Test detecting when Homebrew is installed."""
        mock_command_exists.return_value = True
        
        result = check_homebrew()
        
        assert result is True
        mock_command_exists.assert_called_once_with('brew')
    
    @patch('provision.macos.command_exists')
    def test_check_homebrew_not_installed(self, mock_command_exists):
        """Test detecting when Homebrew is not installed."""
        mock_command_exists.return_value = False
        
        result = check_homebrew()
        
        assert result is False
        mock_command_exists.assert_called_once_with('brew')


class TestHomebrewInstallation:
    """Tests for Homebrew installation."""
    
    @patch('provision.macos.log_action')
    @patch('provision.macos.log_info')
    @patch('provision.macos.sh.bash')
    @patch('provision.macos.sh.curl')
    @patch('provision.macos.check_homebrew')
    def test_install_homebrew_when_not_installed(self, mock_check, mock_curl, mock_bash, mock_log_info, mock_log_action):
        """Test installing Homebrew when it's not installed."""
        mock_check.return_value = False
        mock_curl.return_value = "install script content"
        
        install_homebrew(dry_run=False)
        
        mock_check.assert_called_once()
        mock_log_action.assert_called_with("Homebrew not found. Installing Homebrew...")
        mock_curl.assert_called_once_with("-fsSL", "https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh")
        mock_bash.assert_called_once_with("-c", "install script content")
    
    @patch('provision.macos.log_info')
    @patch('provision.macos.check_homebrew')
    def test_install_homebrew_when_already_installed(self, mock_check, mock_log_info):
        """Test installing Homebrew when it's already installed (idempotent)."""
        mock_check.return_value = True
        
        install_homebrew(dry_run=False)
        
        mock_check.assert_called_once()
        mock_log_info.assert_called_with("Homebrew is already installed.")
    
    @patch('provision.macos.log_action')
    @patch('provision.macos.check_homebrew')
    def test_install_homebrew_dry_run(self, mock_check, mock_log_action):
        """Test installing Homebrew in dry-run mode."""
        mock_check.return_value = False
        
        install_homebrew(dry_run=True)
        
        mock_check.assert_called_once()
        mock_log_action.assert_called_with("[DRY RUN] Would install Homebrew")


class TestBrewfileInstallation:
    """Tests for Brewfile package installation."""
    
    @patch('provision.macos.log_action')
    @patch('provision.macos.sh.brew')
    def test_install_brewfile_packages(self, mock_brew, mock_log_action):
        """Test installing packages from Brewfile."""
        brewfile_path = "/path/to/Brewfile"
        
        install_brewfile_packages(brewfile_path, dry_run=False)
        
        mock_log_action.assert_called_with("Installing packages from Brewfile...")
        mock_brew.assert_called_once_with("bundle", f"--file={brewfile_path}")
    
    @patch('provision.macos.log_action')
    def test_install_brewfile_packages_dry_run(self, mock_log_action):
        """Test installing packages in dry-run mode."""
        brewfile_path = "/path/to/Brewfile"
        
        install_brewfile_packages(brewfile_path, dry_run=True)
        
        mock_log_action.assert_called_with(f"[DRY RUN] Would install packages from {brewfile_path}")
    
    @patch('provision.macos.log_action')
    @patch('provision.macos.sh.brew')
    def test_install_brewfile_packages_with_path_object(self, mock_brew, mock_log_action):
        """Test installing packages with Path object."""
        brewfile_path = Path("/path/to/Brewfile")
        
        install_brewfile_packages(brewfile_path, dry_run=False)
        
        mock_log_action.assert_called_with("Installing packages from Brewfile...")
        mock_brew.assert_called_once_with("bundle", f"--file={brewfile_path}")