"""Utility functions for the provisioning tool."""
import logging
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


class _ShFilter(logging.Filter):
    """Extract just the command from sh's verbose log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        import re
        m = re.search(r"<Command '(.+?)'", record.getMessage())
        if m:
            record.msg = m.group(1)
            record.args = ()
        return True


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    sh_logger = logging.getLogger("sh")
    if verbose:
        sh_logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("  [sh] %(message)s"))
        handler.addFilter(_ShFilter())
        sh_logger.addHandler(handler)
    else:
        sh_logger.setLevel(logging.WARNING)