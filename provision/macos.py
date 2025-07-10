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


def manage_filevault(dry_run: bool = False) -> None:
    """Manage FileVault - disable it for headless boot capability."""
    try:
        # Check FileVault status
        status_output = str(sh.sudo.fdesetup("status"))
        
        if "FileVault is On" in status_output:
            if dry_run:
                log_action("[DRY RUN] Would disable FileVault")
                return
            
            log_action("FileVault is enabled. Disabling for headless boot...")
            sh.sudo.fdesetup("disable")
        else:
            log_info("FileVault is already disabled.")
    except Exception as e:
        log_action(f"Failed to manage FileVault: {e}")


def disable_ssh(dry_run: bool = False) -> None:
    """Disable standard SSH (Remote Login) service."""
    try:
        # Check SSH status
        status_output = str(sh.sudo.systemsetup("-getremotelogin"))
        
        if "Remote Login: On" in status_output:
            if dry_run:
                log_action("[DRY RUN] Would disable SSH (Remote Login)")
                return
            
            log_action("Standard SSH (Remote Login) is enabled. Disabling...")
            sh.sudo.systemsetup("-setremotelogin", "off")
        else:
            log_info("Standard SSH (Remote Login) is already disabled.")
    except Exception as e:
        log_action(f"Failed to disable SSH: {e}")


def configure_firewall(dry_run: bool = False) -> None:
    """Configure macOS firewall with stealth mode and exceptions."""
    SOCKET_FILTER = "/usr/libexec/ApplicationFirewall/socketfilterfw"
    
    try:
        # Check firewall status
        firewall_status = str(getattr(sh.sudo, SOCKET_FILTER)("--getglobalstate"))
        
        if "Firewall is disabled" in firewall_status or "disabled" in firewall_status:
            if dry_run:
                log_action("[DRY RUN] Would enable and configure firewall")
                return
            
            log_action("Firewall is disabled. Enabling firewall...")
            socketfilter = getattr(sh.sudo, SOCKET_FILTER)
            socketfilter("--setglobalstate", "on")
            socketfilter("--setallowsigned", "on")
            socketfilter("--setstealthmode", "on")
        else:
            log_info("Firewall is already enabled.")
        
        if dry_run:
            return
        
        # Configure firewall exceptions
        log_info("Verifying firewall exceptions for continuity services...")
        
        # Get tailscaled path
        tailscaled_path = get_tailscaled_path()
        if not tailscaled_path:
            log_action("WARNING: tailscaled path not found, skipping firewall exception")
            tailscaled_path = None
        
        # Services to add exceptions for
        services_to_check = [
            tailscaled_path,
            "/System/Library/CoreServices/RemoteManagement/ARDAgent.app",
            "/System/Library/CoreServices/UniversalControl.app",
            "/usr/libexec/sharingd",
            "/usr/libexec/rapportd"
        ]
        
        socketfilter = getattr(sh.sudo, SOCKET_FILTER)
        
        for service_path in services_to_check:
            if not service_path:
                continue
                
            try:
                # Check if service is already in firewall list
                list_output = str(socketfilter("--listapps"))
                
                if service_path not in list_output:
                    log_action(f"Adding firewall exception for: {service_path}")
                    socketfilter("--add", service_path)
                
                # Always ensure the app is unblocked
                socketfilter("--unblockapp", service_path)
            except Exception as e:
                # Some services might not exist on all systems
                continue
        
        log_info("Firewall exceptions are configured.")
        
    except Exception as e:
        log_action(f"Failed to configure firewall: {e}")


def enable_screen_sharing(dry_run: bool = False) -> None:
    """Enable Screen Sharing (VNC) service for remote GUI access."""
    try:
        # Check if Screen Sharing service is already loaded
        launchctl_list = str(sh.sudo.launchctl.list())
        
        if "com.apple.screensharing" in launchctl_list:
            log_info("Screen Sharing service is already enabled.")
            return
        
        if dry_run:
            log_action("[DRY RUN] Would enable Screen Sharing service")
            return
        
        log_action("Screen Sharing service is not loaded. Enabling...")
        sh.sudo.launchctl.load("-w", "/System/Library/LaunchDaemons/com.apple.screensharing.plist")
        
    except Exception as e:
        log_action(f"Failed to enable Screen Sharing: {e}")


def configure_power_management(dry_run: bool = False) -> None:
    """Configure power management settings to prevent sleep."""
    try:
        # Get current power management settings
        pmset_output = str(sh.pmset("-g"))
        
        # Check if any changes are needed
        changes_needed = []
        
        # Parse sleep setting
        import re
        sleep_match = re.search(r'^\s*sleep\s+(\d+)', pmset_output, re.MULTILINE)
        if sleep_match and sleep_match.group(1) != "0":
            changes_needed.append(("sleep", "Disabling system sleep..."))
        
        # Parse disksleep setting
        disksleep_match = re.search(r'^\s*disksleep\s+(\d+)', pmset_output, re.MULTILINE)
        if disksleep_match and disksleep_match.group(1) != "0":
            changes_needed.append(("disksleep", "Disabling disk sleep..."))
        
        # Parse powernap setting
        powernap_match = re.search(r'^\s*powernap\s+(\d+)', pmset_output, re.MULTILINE)
        if powernap_match and powernap_match.group(1) != "0":
            changes_needed.append(("powernap", "Disabling Power Nap..."))
        
        if not changes_needed:
            log_info("Power settings are already configured to prevent sleep.")
            return
        
        if dry_run:
            if any(setting[0] == "sleep" for setting in changes_needed):
                log_action("[DRY RUN] Would disable system sleep")
            if any(setting[0] == "disksleep" for setting in changes_needed):
                log_action("[DRY RUN] Would disable disk sleep")
            if any(setting[0] == "powernap" for setting in changes_needed):
                log_action("[DRY RUN] Would disable Power Nap")
            return
        
        # Apply changes
        for setting_name, log_message in changes_needed:
            log_action(log_message)
            sh.pmset("-a", setting_name, "0")
        
        log_info("Power settings configured to prevent sleep.")
        
    except Exception as e:
        log_action(f"Failed to configure power management: {e}")


def verify_docker_stack() -> None:
    """Verify Docker stack is working correctly."""
    log_info("Verifying Docker stack...")
    
    # Wait a moment for services to be ready
    import time
    time.sleep(2)
    
    # Check if DOCKER_HOST is configured
    docker_host = os.environ.get('DOCKER_HOST')
    if not docker_host:
        log_action("DOCKER_HOST is not set. Please configure your shell as shown at the end of this script.")
    else:
        log_info(f"DOCKER_HOST is set to: {docker_host}")
    
    # Check if Colima is actually running
    try:
        sh.colima.status()
        log_info("Colima runtime is running.")
        
        # Only test Docker if Colima is running
        try:
            sh.docker.ps()
            log_info("Docker daemon is accessible.")
        except Exception:
            log_action("Docker daemon is not accessible. Check DOCKER_HOST and Colima status.")
        
        try:
            sh.docker.compose.ls()
            log_info("Docker Compose is working.")
        except Exception:
            log_action("Docker Compose is not working properly.")
    except Exception:
        log_action("Colima is not running. Docker commands will fail until Colima is started.")
        log_action("The LaunchAgent may have failed to start Colima automatically.")
        log_action("Try running 'colima start' manually to start the Docker runtime.")


def verify_tailscale_connectivity() -> bool:
    """Verify Tailscale connectivity. Returns True if connected."""
    log_info("Verifying Tailscale connectivity...")
    
    try:
        status_output = str(sh.tailscale.status())
        
        if "active" in status_output:
            log_info("Tailscale is already active.")
            return True
        else:
            log_info("Tailscale is not connected. The final step is to connect to your Tailnet.")
            log_info("Please run the following command and follow the authentication link:")
            log_info("\n    sudo tailscale up\n")
            return False
    except Exception as e:
        log_info(f"Failed to check Tailscale status: {e}")
        return False