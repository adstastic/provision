"""Tests for the main provisioning workflow steps."""
import pytest
from unittest.mock import patch, MagicMock
import platform
from pathlib import Path

from provision.steps import provision_system


class TestProvisionSystem:
    """Tests for the main provisioning workflow."""
    
    @patch('provision.steps.platform.system')
    @patch('provision.steps.install_dependencies')
    def test_provision_system_on_macos(self, mock_install_deps, mock_platform):
        """Test provisioning workflow on macOS."""
        mock_platform.return_value = 'Darwin'
        
        provision_system(dry_run=False, user_only=False)
        
        mock_install_deps.assert_called_once_with(dry_run=False, user_only=False)
    
    @patch('provision.steps.platform.system')
    @patch('provision.steps.install_dependencies')
    def test_provision_system_dry_run(self, mock_install_deps, mock_platform):
        """Test provisioning workflow in dry-run mode."""
        mock_platform.return_value = 'Darwin'
        
        provision_system(dry_run=True, user_only=False)
        
        mock_install_deps.assert_called_once_with(dry_run=True, user_only=False)
    
    @patch('provision.steps.platform.system')
    @patch('provision.steps.install_dependencies')
    def test_provision_system_user_only(self, mock_install_deps, mock_platform):
        """Test provisioning workflow in user-only mode."""
        mock_platform.return_value = 'Darwin'
        
        provision_system(dry_run=False, user_only=True)
        
        mock_install_deps.assert_called_once_with(dry_run=False, user_only=True)
    
    @patch('provision.steps.platform.system')
    def test_provision_system_unsupported_platform(self, mock_platform):
        """Test provisioning workflow on unsupported platform."""
        mock_platform.return_value = 'Windows'
        
        with pytest.raises(NotImplementedError, match="Platform Windows is not supported"):
            provision_system(dry_run=False, user_only=False)


class TestInstallDependencies:
    """Tests for dependency installation step."""
    
    @patch('provision.steps.get_script_directory')
    @patch('provision.macos.install_brewfile_packages')
    @patch('provision.macos.install_homebrew')
    @patch('provision.steps.platform.system')
    def test_install_dependencies_macos(self, mock_platform, mock_install_brew, mock_install_packages, mock_get_dir):
        """Test installing dependencies on macOS."""
        from provision.steps import install_dependencies
        
        mock_platform.return_value = 'Darwin'
        mock_get_dir.return_value = Path("/path/to/provision")
        
        install_dependencies(dry_run=False, user_only=False)
        
        mock_install_brew.assert_called_once_with(dry_run=False)
        expected_brewfile = Path("/path/to/provision/macos/Brewfile")
        mock_install_packages.assert_called_once_with(expected_brewfile, dry_run=False)
    
    @patch('provision.macos.install_brewfile_packages')
    @patch('provision.macos.install_homebrew')
    @patch('provision.steps.platform.system')
    def test_install_dependencies_user_only_skips_homebrew(self, mock_platform, mock_install_brew, mock_install_packages):
        """Test that user-only mode skips Homebrew installation."""
        from provision.steps import install_dependencies
        
        mock_platform.return_value = 'Darwin'
        
        install_dependencies(dry_run=False, user_only=True)
        
        # Homebrew installation requires root, so should be skipped in user-only mode
        mock_install_brew.assert_not_called()
        # But packages should still be installed
        mock_install_packages.assert_called_once()