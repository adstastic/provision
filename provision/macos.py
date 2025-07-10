"""macOS-specific provisioning functions."""
import sh
import re
import json
import os
from pathlib import Path
from typing import Union, Optional
from provision.utils import command_exists, log_info, log_action, get_real_user, get_real_home


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


def setup_tmux_service(dry_run: bool = False) -> None:
    """Setup tmux service as LaunchAgent."""
    if dry_run:
        log_action("[DRY RUN] Would setup tmux service")
        return
    
    # Get real user info (handle sudo)
    real_user = get_real_user()
    real_home = get_real_home()
    
    if not real_user or real_user == "root":
        log_info("Skipping tmux service for root user.")
        return
    
    log_info(f"Setting up tmux service for user: {real_user}")
    
    # Create LaunchAgents directory if it doesn't exist
    launch_agents_dir = Path(real_home) / "Library" / "LaunchAgents"
    if not launch_agents_dir.exists():
        log_action("Creating LaunchAgents directory...")
        sh.sudo("-u", real_user, "mkdir", "-p", str(launch_agents_dir))
    
    # Get tmux binary path
    try:
        tmux_path = str(sh.which("tmux")).strip()
    except Exception:
        raise RuntimeError("tmux binary not found")
    
    log_info(f"Using tmux found at: {tmux_path}")
    
    # Create tmux service plist
    plist_path = launch_agents_dir / "com.tmux.main.plist"
    if not plist_path.exists():
        log_action("Creating tmux service plist...")
        
        # Read template and replace placeholder
        template_path = Path(__file__).parent / "configs" / "com.tmux.main.plist"
        with open(template_path, 'r') as f:
            plist_content = f.read()
        
        plist_content = plist_content.replace("TMUX_PATH_PLACEHOLDER", tmux_path)
        
        # Write plist file as the real user
        with open(plist_path, 'w') as f:
            f.write(plist_content)
        
        # Set proper ownership
        sh.sudo("chown", f"{real_user}:staff", str(plist_path))
    else:
        log_info("tmux service plist already exists.")
    
    # Load the service if not already loaded
    try:
        launchctl_list = str(sh.launchctl("list"))
        if "com.tmux.main" not in launchctl_list:
            log_action("Loading tmux service...")
            sh.sudo("-u", real_user, "launchctl", "load", str(plist_path))
            log_info("tmux service loaded successfully.")
        else:
            log_info("tmux service is already loaded.")
    except Exception as e:
        log_action(f"Failed to load tmux service: {e}")


def setup_colima_service(dry_run: bool = False) -> None:
    """Setup Colima Docker service via Homebrew services."""
    if dry_run:
        log_action("[DRY RUN] Would setup Colima service")
        return
    
    # Get real user info
    real_user = get_real_user()
    
    if not real_user or real_user == "root":
        log_info("Skipping Colima service for root user.")
        return
    
    log_info("Setting up Colima service...")
    
    # Check if we're in tmux and need reattach-to-user-namespace
    if os.environ.get('TMUX') and not command_exists('reattach-to-user-namespace'):
        log_action("Installing reattach-to-user-namespace for tmux compatibility...")
        sh.brew("install", "reattach-to-user-namespace")
    
    # Check if Colima service is already started
    try:
        services_list = str(sh.brew.services.list())
        # Check if colima line contains "started"
        for line in services_list.split('\n'):
            if "colima" in line and "started" in line:
                log_info("Colima service is already running.")
                return
    except Exception:
        # brew services might not be available
        pass
    
    # Start Colima service
    log_action("Starting Colima service via Homebrew services...")
    try:
        sh.brew.services.start("colima")
        log_info("Colima service started successfully.")
        
        # Wait a bit for Colima to initialize
        import time
        time.sleep(5)
        
        # Verify Colima is running
        try:
            sh.colima.status()
            log_info("Colima is running.")
        except Exception:
            log_action("WARNING: Colima service started but Colima is not yet ready.")
            log_action("It may take a moment to fully initialize.")
    except Exception as e:
        log_action(f"Failed to start Colima service: {e}")