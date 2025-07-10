"""Provisioning workflow steps."""
import platform
from pathlib import Path
from provision.utils import log_info


def get_script_directory() -> Path:
    """Get the directory where this module is located."""
    return Path(__file__).parent.parent.resolve()


def install_dependencies(dry_run: bool = False, user_only: bool = False) -> None:
    """Install system dependencies based on the platform."""
    current_platform = platform.system()
    
    if current_platform == 'Darwin':
        log_info("Installing dependencies for macOS...")
        
        if not user_only:
            # Homebrew installation requires admin privileges
            from provision.macos import install_homebrew
            install_homebrew(dry_run=dry_run)
        
        # Install packages from Brewfile
        from provision.macos import install_brewfile_packages
        brewfile_path = get_script_directory() / "macos" / "Brewfile"
        install_brewfile_packages(brewfile_path, dry_run=dry_run)
    else:
        raise NotImplementedError(f"Platform {current_platform} is not supported yet")


def setup_tailscale(dry_run: bool = False, user_only: bool = False) -> None:
    """Setup Tailscale based on the platform."""
    current_platform = platform.system()
    
    if current_platform == 'Darwin':
        log_info("Setting up Tailscale for macOS...")
        
        # Install Tailscale binaries
        from provision.macos import install_tailscale
        install_tailscale(dry_run=dry_run)
        
        if not user_only:
            # Install system daemon (requires root)
            from provision.macos import install_tailscale_daemon
            install_tailscale_daemon(dry_run=dry_run)
            
            # Configure DNS (requires root)
            from provision.macos import configure_tailscale_dns
            configure_tailscale_dns(dry_run=dry_run)
    else:
        raise NotImplementedError(f"Platform {current_platform} is not supported yet")


def configure_services(dry_run: bool = False, user_only: bool = False) -> None:
    """Configure services based on the platform."""
    current_platform = platform.system()
    
    if current_platform == 'Darwin':
        log_info("Configuring services for macOS...")
        
        # Both services are user-level, so we always run them
        from provision.macos import setup_tmux_service, setup_colima_service
        setup_tmux_service(dry_run=dry_run)
        setup_colima_service(dry_run=dry_run)
    else:
        raise NotImplementedError(f"Platform {current_platform} is not supported yet")


def provision_system(dry_run: bool = False, user_only: bool = False) -> None:
    """Main provisioning workflow - delegates to platform-specific implementations."""
    current_platform = platform.system()
    
    if current_platform not in ['Darwin', 'Linux']:
        raise NotImplementedError(f"Platform {current_platform} is not supported")
    
    # Phase 1: Install dependencies
    install_dependencies(dry_run=dry_run, user_only=user_only)
    
    # Phase 2: Tailscale setup
    setup_tailscale(dry_run=dry_run, user_only=user_only)
    
    # Phase 3: Service configuration
    configure_services(dry_run=dry_run, user_only=user_only)
    
    # TODO: Phase 4: Security configuration
    # TODO: Phase 5: System configuration
    # TODO: Phase 6: Verification