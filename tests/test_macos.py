"""Tests for macOS-specific provisioning functions."""
import pytest
from unittest.mock import patch, MagicMock, call
import sh
from pathlib import Path

from provision.macos import (
    check_homebrew, install_homebrew, install_brewfile_packages,
    check_tailscale, get_installed_tailscale_version, get_latest_tailscale_version,
    is_tailscale_up_to_date
)


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


class TestTailscaleCheck:
    """Tests for Tailscale detection."""
    
    @patch('provision.macos.command_exists')
    def test_check_tailscale_installed(self, mock_command_exists):
        """Test detecting when Tailscale is installed."""
        mock_command_exists.return_value = True
        
        result = check_tailscale()
        
        assert result is True
        mock_command_exists.assert_called_once_with('tailscaled')
    
    @patch('provision.macos.command_exists')
    def test_check_tailscale_not_installed(self, mock_command_exists):
        """Test detecting when Tailscale is not installed."""
        mock_command_exists.return_value = False
        
        result = check_tailscale()
        
        assert result is False
        mock_command_exists.assert_called_once_with('tailscaled')


class TestTailscaleVersion:
    """Tests for Tailscale version checking."""
    
    @patch('provision.macos.sh.tailscale')
    def test_get_installed_tailscale_version(self, mock_tailscale):
        """Test getting the installed Tailscale version."""
        mock_tailscale.return_value = "  tailscale commit: 1234567890abcdef\n  other/third/v1.58.2-t1234567890a\n  go version: go1.21.1\n"
        
        version = get_installed_tailscale_version()
        
        assert version == "1.58.2"
        mock_tailscale.assert_called_once_with("version")
    
    @patch('provision.macos.sh.tailscale')
    def test_get_installed_tailscale_version_not_found(self, mock_tailscale):
        """Test getting version when tailscale command fails."""
        mock_tailscale.side_effect = sh.ErrorReturnCode_1("tailscale", b"", b"command not found")
        
        version = get_installed_tailscale_version()
        
        assert version is None
    
    @patch('provision.macos.sh.curl')
    def test_get_latest_tailscale_version(self, mock_curl):
        """Test getting the latest Tailscale version from GitHub."""
        mock_response = '{"tag_name": "v1.60.0", "name": "v1.60.0"}'
        mock_curl.return_value = mock_response
        
        version = get_latest_tailscale_version()
        
        assert version == "1.60.0"
        mock_curl.assert_called_once_with(
            "-s",
            "https://api.github.com/repos/tailscale/tailscale/releases/latest"
        )
    
    @patch('provision.macos.sh.curl')
    def test_get_latest_tailscale_version_error(self, mock_curl):
        """Test handling errors when fetching latest version."""
        mock_curl.side_effect = sh.ErrorReturnCode_1("curl", b"", b"network error")
        
        version = get_latest_tailscale_version()
        
        assert version is None
    
    @patch('provision.macos.get_latest_tailscale_version')
    @patch('provision.macos.get_installed_tailscale_version')
    def test_is_tailscale_up_to_date_true(self, mock_installed, mock_latest):
        """Test when Tailscale is up to date."""
        mock_installed.return_value = "1.60.0"
        mock_latest.return_value = "1.60.0"
        
        result = is_tailscale_up_to_date()
        
        assert result is True
    
    @patch('provision.macos.get_latest_tailscale_version')
    @patch('provision.macos.get_installed_tailscale_version')
    def test_is_tailscale_up_to_date_false(self, mock_installed, mock_latest):
        """Test when Tailscale is outdated."""
        mock_installed.return_value = "1.58.2"
        mock_latest.return_value = "1.60.0"
        
        result = is_tailscale_up_to_date()
        
        assert result is False
    
    @patch('provision.macos.get_latest_tailscale_version')
    @patch('provision.macos.get_installed_tailscale_version')
    def test_is_tailscale_up_to_date_not_installed(self, mock_installed, mock_latest):
        """Test when Tailscale is not installed."""
        mock_installed.return_value = None
        mock_latest.return_value = "1.60.0"
        
        result = is_tailscale_up_to_date()
        
        assert result is False
    
    @patch('provision.macos.get_latest_tailscale_version')
    @patch('provision.macos.get_installed_tailscale_version')
    def test_is_tailscale_up_to_date_cannot_check(self, mock_installed, mock_latest):
        """Test when we cannot determine the latest version."""
        mock_installed.return_value = "1.58.2"
        mock_latest.return_value = None
        
        result = is_tailscale_up_to_date()
        
        # If we can't get the latest version, assume current is up to date
        assert result is True