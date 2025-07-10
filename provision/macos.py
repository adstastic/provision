"""macOS-specific provisioning functions."""
import sh
import re
import json
import os
from pathlib import Path
from typing import Union, Optional
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


def install_brewfile_packages(brewfile_path: Union[str, Path], dry_run: bool = False) -> None:
    """Install packages from a Brewfile."""
    if dry_run:
        log_action(f"[DRY RUN] Would install packages from {brewfile_path}")
        return
    
    log_action("Installing packages from Brewfile...")
    sh.brew("bundle", f"--file={brewfile_path}")


def check_tailscale() -> bool:
    """Check if Tailscale is installed."""
    return command_exists('tailscaled')


def get_installed_tailscale_version() -> Optional[str]:
    """Get the installed Tailscale version."""
    try:
        output = str(sh.tailscale("version"))
        # Parse version from output like "other/third/v1.58.2-t1234567890a"
        match = re.search(r'/v(\d+\.\d+\.\d+)', output)
        if match:
            return match.group(1)
        return None
    except Exception:  # sh raises various ErrorReturnCode_X exceptions
        return None


def get_latest_tailscale_version() -> Optional[str]:
    """Get the latest Tailscale version from GitHub."""
    try:
        response = str(sh.curl("-s", "https://api.github.com/repos/tailscale/tailscale/releases/latest"))
        data = json.loads(response)
        tag = data.get('tag_name', '')
        # Remove 'v' prefix if present
        if tag.startswith('v'):
            return tag[1:]
        return tag if tag else None
    except (Exception, json.JSONDecodeError, KeyError):
        return None


def is_tailscale_up_to_date() -> bool:
    """Check if Tailscale is up to date."""
    installed = get_installed_tailscale_version()
    if installed is None:
        return False
    
    latest = get_latest_tailscale_version()
    if latest is None:
        # Can't determine latest version, assume current is ok
        return True
    
    return installed == latest


def install_tailscale(dry_run: bool = False) -> None:
    """Install or update Tailscale from source."""
    if check_tailscale():
        if is_tailscale_up_to_date():
            log_info("Tailscale is already installed and up to date.")
            return
        else:
            if dry_run:
                log_action("[DRY RUN] Would update Tailscale from source")
                return
            log_action("Tailscale is outdated. Updating from source...")
    else:
        if dry_run:
            log_action("[DRY RUN] Would install Tailscale from source")
            return
        log_action("tailscaled not found. Installing Tailscale from source...")
    
    # Get GOPATH and update PATH
    gopath = str(sh.go("env", "GOPATH")).strip()
    os.environ['PATH'] = f"{os.environ.get('PATH', '')}:{gopath}/bin"
    
    # Install both tailscale and tailscaled
    sh.go("install", "tailscale.com/cmd/tailscale@main", "tailscale.com/cmd/tailscaled@main")


def get_tailscaled_path() -> Optional[str]:
    """Get the path to the tailscaled binary."""
    try:
        return str(sh.which("tailscaled")).strip()
    except Exception:  # sh raises various ErrorReturnCode_X exceptions
        return None


def install_tailscale_daemon(dry_run: bool = False) -> None:
    """Install Tailscale as a system daemon."""
    daemon_plist = Path("/Library/LaunchDaemons/com.tailscale.tailscaled.plist")
    
    if daemon_plist.exists():
        log_info("Tailscale system daemon is already installed.")
        return
    
    if dry_run:
        log_action("[DRY RUN] Would install Tailscale system daemon")
        return
    
    # Get tailscaled path
    tailscaled_path = get_tailscaled_path()
    if not tailscaled_path:
        raise RuntimeError("tailscaled binary not found")
    
    log_action("Tailscale system daemon not found. Installing...")
    sh.sudo(tailscaled_path, "install-system-daemon")


def configure_tailscale_dns(dry_run: bool = False) -> None:
    """Configure system to use Tailscale MagicDNS."""
    TAILSCALE_DNS = "100.100.100.100"
    
    # Get list of network interfaces
    hardware_ports = str(sh.networksetup("-listallhardwareports"))
    
    # Common network interfaces to configure
    interfaces = ["Wi-Fi", "Ethernet"]
    
    for interface in interfaces:
        if f"Hardware Port: {interface}" not in hardware_ports:
            continue
            
        try:
            # Get current DNS servers
            current_dns = str(sh.networksetup("-getdnsservers", interface))
            
            # Check if Tailscale DNS is already configured
            if TAILSCALE_DNS in current_dns:
                log_info(f"Tailscale DNS already configured for {interface}.")
                continue
            
            if dry_run:
                log_action(f"[DRY RUN] Would configure Tailscale DNS for {interface}")
                continue
            
            # Get current DNS servers again for the actual configuration
            current_dns_list = []
            try:
                dns_output = str(sh.networksetup("-getdnsservers", interface))
                if "There aren't any" not in dns_output and dns_output.strip():
                    current_dns_list = dns_output.strip().split('\n')
            except Exception:
                pass
            
            # Prepend Tailscale DNS to existing DNS servers
            new_dns_list = [TAILSCALE_DNS] + current_dns_list
            
            log_action(f"Adding Tailscale DNS to {interface}...")
            sh.sudo.networksetup("-setdnsservers", interface, *new_dns_list)
            
        except Exception as e:
            # Interface might not exist or be configured
            continue