"""macOS-specific provisioning functions."""
import sh
from provision.utils import command_exists, log_info, log_action


def check_homebrew() -> bool:
    """Check if Homebrew is installed."""
    return command_exists('brew')


def install_homebrew(dry_run: bool = False) -> None:
    """Install Homebrew if not already installed."""
    if check_homebrew():
        log_info("Homebrew is already installed.")
        return
    
    if dry_run:
        log_action("[DRY RUN] Would install Homebrew")
        return
    
    log_action("Homebrew not found. Installing Homebrew...")
    install_script = sh.curl("-fsSL", "https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh")
    sh.bash("-c", install_script)