"""Tests for macOS-specific provisioning functions."""
import pytest
from unittest.mock import patch, MagicMock

from provision.macos import check_homebrew


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