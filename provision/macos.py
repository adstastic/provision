"""macOS-specific provisioning functions."""
from provision.utils import command_exists


def check_homebrew() -> bool:
    """Check if Homebrew is installed."""
    return command_exists('brew')