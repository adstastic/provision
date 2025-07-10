"""Tests for provision.utils module."""
import pytest
from unittest.mock import patch, MagicMock
from provision import utils


def test_command_exists_when_command_found():
    """Test command_exists returns True when command is found."""
    with patch('shutil.which', return_value='/usr/bin/git'):
        assert utils.command_exists('git') is True


def test_command_exists_when_command_not_found():
    """Test command_exists returns False when command not found."""
    with patch('shutil.which', return_value=None):
        assert utils.command_exists('nonexistent') is False


def test_is_root_when_root():
    """Test is_root returns True when running as root."""
    with patch('os.geteuid', return_value=0):
        assert utils.is_root() is True


def test_is_root_when_not_root():
    """Test is_root returns False when not running as root."""
    with patch('os.geteuid', return_value=1000):
        assert utils.is_root() is False


def test_get_real_user_when_sudo():
    """Test get_real_user returns SUDO_USER when running with sudo."""
    with patch.dict('os.environ', {'SUDO_USER': 'testuser', 'USER': 'root'}):
        assert utils.get_real_user() == 'testuser'


def test_get_real_user_when_not_sudo():
    """Test get_real_user returns USER when not running with sudo."""
    with patch.dict('os.environ', {'USER': 'normaluser'}, clear=True):
        assert utils.get_real_user() == 'normaluser'


def test_get_real_home_when_sudo():
    """Test get_real_home returns sudo user's home."""
    with patch.dict('os.environ', {'SUDO_USER': 'testuser'}):
        with patch('os.path.expanduser', return_value='/home/testuser'):
            assert utils.get_real_home() == '/home/testuser'


def test_get_real_home_when_not_sudo():
    """Test get_real_home returns current user's home."""
    with patch.dict('os.environ', {'HOME': '/home/normaluser'}, clear=True):
        assert utils.get_real_home() == '/home/normaluser'


def test_log_info(capsys):
    """Test log_info outputs formatted message."""
    utils.log_info("Test message")
    captured = capsys.readouterr()
    assert "[INFO] Test message\n" == captured.out


def test_log_action(capsys):
    """Test log_action outputs indented message."""
    utils.log_action("Installing package")
    captured = capsys.readouterr()
    assert "  -> Installing package\n" == captured.out


def test_setup_logging_verbose(capsys):
    """Test setup_logging in verbose mode."""
    utils.setup_logging(verbose=True)
    # In real implementation, this would configure logging level
    # For now, just test it doesn't crash
    assert True


def test_setup_logging_normal(capsys):
    """Test setup_logging in normal mode."""
    utils.setup_logging(verbose=False)
    # In real implementation, this would configure logging level
    # For now, just test it doesn't crash
    assert True