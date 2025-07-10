"""Utility functions for the provisioning tool."""
import os
import shutil
from pathlib import Path


def command_exists(command: str) -> bool:
    """Check if a command exists in the system PATH."""
    return shutil.which(command) is not None


def is_root() -> bool:
    """Check if the script is running as root."""
    return os.geteuid() == 0


def get_real_user() -> str:
    """Get the real username (handles sudo)."""
    return os.environ.get('SUDO_USER', os.environ.get('USER', ''))


def get_real_home() -> str:
    """Get the real user's home directory (handles sudo)."""
    sudo_user = os.environ.get('SUDO_USER')
    if sudo_user:
        return os.path.expanduser(f'~{sudo_user}')
    return os.environ.get('HOME', '')


def log_info(message: str) -> None:
    """Log an informational message."""
    print(f"[INFO] {message}")


def log_action(message: str) -> None:
    """Log an action being performed."""
    print(f"  -> {message}")


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    # In the future, this could configure Python logging
    # For now, it's a placeholder that accepts the verbose flag
    pass