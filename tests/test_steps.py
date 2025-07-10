"""Tests for the main provisioning workflow steps."""
import pytest
from unittest.mock import patch, MagicMock
import platform
from pathlib import Path

from provision.steps import provision_system


class TestProvisionSystem:
    """Tests for the main provisioning workflow."""
    
    @patch('provision.steps.platform.system')
    @patch('provision.steps.verify_system')
    @patch('provision.steps.configure_system')
    @patch('provision.steps.configure_security')
    @patch('provision.steps.configure_services')
    @patch('provision.steps.setup_tailscale')
    @patch('provision.steps.install_dependencies')
    def test_provision_system_on_macos(self, mock_install_deps, mock_setup_ts, mock_configure_services, 
                                      mock_configure_security, mock_configure_system, mock_verify_system, mock_platform):
        """Test provisioning workflow on macOS."""
        mock_platform.return_value = 'Darwin'
        
        provision_system(dry_run=False, user_only=False)
        
        mock_install_deps.assert_called_once_with(dry_run=False, user_only=False)
        mock_setup_ts.assert_called_once_with(dry_run=False, user_only=False)
        mock_configure_services.assert_called_once_with(dry_run=False, user_only=False)
        mock_configure_security.assert_called_once_with(dry_run=False, user_only=False)
        mock_configure_system.assert_called_once_with(dry_run=False, user_only=False)
        mock_verify_system.assert_called_once()
    
    @patch('provision.steps.platform.system')
    @patch('provision.steps.verify_system')
    @patch('provision.steps.configure_system')
    @patch('provision.steps.configure_security')
    @patch('provision.steps.configure_services')
    @patch('provision.steps.setup_tailscale')
    @patch('provision.steps.install_dependencies')
    def test_provision_system_dry_run(self, mock_install_deps, mock_setup_ts, mock_configure_services, 
                                     mock_configure_security, mock_configure_system, mock_verify_system, mock_platform):
        """Test provisioning workflow in dry-run mode."""
        mock_platform.return_value = 'Darwin'
        
        provision_system(dry_run=True, user_only=False)
        
        mock_install_deps.assert_called_once_with(dry_run=True, user_only=False)
        mock_setup_ts.assert_called_once_with(dry_run=True, user_only=False)
        mock_configure_services.assert_called_once_with(dry_run=True, user_only=False)
        mock_configure_security.assert_called_once_with(dry_run=True, user_only=False)
        mock_configure_system.assert_called_once_with(dry_run=True, user_only=False)
        mock_verify_system.assert_called_once()
    
    @patch('provision.steps.platform.system')
    @patch('provision.steps.verify_system')
    @patch('provision.steps.configure_system')
    @patch('provision.steps.configure_security')
    @patch('provision.steps.configure_services')
    @patch('provision.steps.setup_tailscale')
    @patch('provision.steps.install_dependencies')
    def test_provision_system_user_only(self, mock_install_deps, mock_setup_ts, mock_configure_services,
                                       mock_configure_security, mock_configure_system, mock_verify_system, mock_platform):
        """Test provisioning workflow in user-only mode."""
        mock_platform.return_value = 'Darwin'
        
        provision_system(dry_run=False, user_only=True)
        
        mock_install_deps.assert_called_once_with(dry_run=False, user_only=True)
        mock_setup_ts.assert_called_once_with(dry_run=False, user_only=True)
        mock_configure_services.assert_called_once_with(dry_run=False, user_only=True)
        mock_configure_security.assert_called_once_with(dry_run=False, user_only=True)
        mock_configure_system.assert_called_once_with(dry_run=False, user_only=True)
        mock_verify_system.assert_called_once()
    
    @patch('provision.steps.platform.system')
    def test_provision_system_unsupported_platform(self, mock_platform):
        """Test provisioning workflow on unsupported platform."""
        mock_platform.return_value = 'Windows'
        
        with pytest.raises(NotImplementedError, match="Platform Windows is not supported"):
            provision_system(dry_run=False, user_only=False)


class TestInstallDependencies:
    """Tests for dependency installation step."""
    
    @patch('provision.steps.get_script_directory')
    @patch('provision.macos.install_brewfile_packages')
    @patch('provision.macos.install_homebrew')
    @patch('provision.steps.platform.system')
    def test_install_dependencies_macos(self, mock_platform, mock_install_brew, mock_install_packages, mock_get_dir):
        """Test installing dependencies on macOS."""
        from provision.steps import install_dependencies
        
        mock_platform.return_value = 'Darwin'
        mock_get_dir.return_value = Path("/path/to/provision")
        
        install_dependencies(dry_run=False, user_only=False)
        
        mock_install_brew.assert_called_once_with(dry_run=False)
        expected_brewfile = Path("/path/to/provision/macos/Brewfile")
        mock_install_packages.assert_called_once_with(expected_brewfile, dry_run=False)
    
    @patch('provision.macos.install_brewfile_packages')
    @patch('provision.macos.install_homebrew')
    @patch('provision.steps.platform.system')
    def test_install_dependencies_user_only_skips_homebrew(self, mock_platform, mock_install_brew, mock_install_packages):
        """Test that user-only mode skips Homebrew installation."""
        from provision.steps import install_dependencies
        
        mock_platform.return_value = 'Darwin'
        
        install_dependencies(dry_run=False, user_only=True)
        
        # Homebrew installation requires root, so should be skipped in user-only mode
        mock_install_brew.assert_not_called()
        # But packages should still be installed
        mock_install_packages.assert_called_once()


class TestTailscaleSetup:
    """Tests for Tailscale setup phase."""
    
    @patch('provision.steps.log_info')
    @patch('provision.steps.platform.system')
    def test_setup_tailscale_macos(self, mock_platform, mock_log_info):
        """Test Tailscale setup on macOS."""
        mock_platform.return_value = 'Darwin'
        
        with patch('provision.macos.install_tailscale') as mock_install_ts, \
             patch('provision.macos.install_tailscale_daemon') as mock_install_daemon, \
             patch('provision.macos.configure_tailscale_dns') as mock_configure_dns:
            
            from provision.steps import setup_tailscale
            setup_tailscale(dry_run=False, user_only=False)
            
            # Should call all Tailscale setup functions
            mock_install_ts.assert_called_once_with(dry_run=False)
            mock_install_daemon.assert_called_once_with(dry_run=False)
            mock_configure_dns.assert_called_once_with(dry_run=False)
    
    @patch('provision.steps.log_info')
    @patch('provision.steps.platform.system')
    def test_setup_tailscale_macos_user_only(self, mock_platform, mock_log_info):
        """Test Tailscale setup in user-only mode (skips daemon)."""
        mock_platform.return_value = 'Darwin'
        
        with patch('provision.macos.install_tailscale') as mock_install_ts, \
             patch('provision.macos.install_tailscale_daemon') as mock_install_daemon, \
             patch('provision.macos.configure_tailscale_dns') as mock_configure_dns:
            
            from provision.steps import setup_tailscale
            setup_tailscale(dry_run=False, user_only=True)
            
            # Should only install Tailscale, not daemon or DNS
            mock_install_ts.assert_called_once_with(dry_run=False)
            mock_install_daemon.assert_not_called()
            mock_configure_dns.assert_not_called()


class TestServiceConfiguration:
    """Tests for service configuration phase."""
    
    @patch('provision.steps.log_info')
    @patch('provision.steps.platform.system')
    def test_configure_services_macos(self, mock_platform, mock_log_info):
        """Test service configuration on macOS."""
        mock_platform.return_value = 'Darwin'
        
        with patch('provision.macos.setup_tmux_service') as mock_setup_tmux, \
             patch('provision.macos.setup_colima_service') as mock_setup_colima:
            
            from provision.steps import configure_services
            configure_services(dry_run=False, user_only=False)
            
            # Should call both service setup functions
            mock_setup_tmux.assert_called_once_with(dry_run=False)
            mock_setup_colima.assert_called_once_with(dry_run=False)
    
    @patch('provision.steps.log_info')
    @patch('provision.steps.platform.system')
    def test_configure_services_macos_dry_run(self, mock_platform, mock_log_info):
        """Test service configuration in dry-run mode."""
        mock_platform.return_value = 'Darwin'
        
        with patch('provision.macos.setup_tmux_service') as mock_setup_tmux, \
             patch('provision.macos.setup_colima_service') as mock_setup_colima:
            
            from provision.steps import configure_services
            configure_services(dry_run=True, user_only=False)
            
            # Should call both with dry_run=True
            mock_setup_tmux.assert_called_once_with(dry_run=True)
            mock_setup_colima.assert_called_once_with(dry_run=True)


class TestSecurityConfiguration:
    """Tests for security configuration phase."""
    
    @patch('provision.steps.log_info')
    @patch('provision.steps.platform.system')
    def test_configure_security_macos(self, mock_platform, mock_log_info):
        """Test security configuration on macOS."""
        mock_platform.return_value = 'Darwin'
        
        with patch('provision.macos.manage_filevault') as mock_filevault, \
             patch('provision.macos.disable_ssh') as mock_ssh, \
             patch('provision.macos.configure_firewall') as mock_firewall:
            
            from provision.steps import configure_security
            configure_security(dry_run=False, user_only=False)
            
            # Should call all security functions
            mock_filevault.assert_called_once_with(dry_run=False)
            mock_ssh.assert_called_once_with(dry_run=False)
            mock_firewall.assert_called_once_with(dry_run=False)
    
    @patch('provision.steps.log_info')
    @patch('provision.steps.platform.system')
    def test_configure_security_macos_dry_run(self, mock_platform, mock_log_info):
        """Test security configuration in dry-run mode."""
        mock_platform.return_value = 'Darwin'
        
        with patch('provision.macos.manage_filevault') as mock_filevault, \
             patch('provision.macos.disable_ssh') as mock_ssh, \
             patch('provision.macos.configure_firewall') as mock_firewall:
            
            from provision.steps import configure_security
            configure_security(dry_run=True, user_only=False)
            
            # Should call all with dry_run=True
            mock_filevault.assert_called_once_with(dry_run=True)
            mock_ssh.assert_called_once_with(dry_run=True)
            mock_firewall.assert_called_once_with(dry_run=True)
    
    @patch('provision.steps.log_info')
    @patch('provision.steps.platform.system')
    def test_configure_security_macos_user_only(self, mock_platform, mock_log_info):
        """Test security configuration in user-only mode (skips root operations)."""
        mock_platform.return_value = 'Darwin'
        
        with patch('provision.macos.manage_filevault') as mock_filevault, \
             patch('provision.macos.disable_ssh') as mock_ssh, \
             patch('provision.macos.configure_firewall') as mock_firewall:
            
            from provision.steps import configure_security
            configure_security(dry_run=False, user_only=True)
            
            # Should skip all security functions (they all require root)
            mock_filevault.assert_not_called()
            mock_ssh.assert_not_called()
            mock_firewall.assert_not_called()
            
            # Should log that we're skipping
            assert any("Skipping security configuration" in str(call) for call in mock_log_info.call_args_list)


class TestSystemConfiguration:
    """Tests for system configuration phase."""
    
    @patch('provision.steps.log_info')
    @patch('provision.steps.platform.system')
    def test_configure_system_macos(self, mock_platform, mock_log_info):
        """Test system configuration on macOS."""
        mock_platform.return_value = 'Darwin'
        
        with patch('provision.macos.enable_screen_sharing') as mock_screen_sharing, \
             patch('provision.macos.configure_power_management') as mock_power_mgmt:
            
            from provision.steps import configure_system
            configure_system(dry_run=False, user_only=False)
            
            # Should call both system functions
            mock_screen_sharing.assert_called_once_with(dry_run=False)
            mock_power_mgmt.assert_called_once_with(dry_run=False)
    
    @patch('provision.steps.log_info')
    @patch('provision.steps.platform.system')
    def test_configure_system_macos_dry_run(self, mock_platform, mock_log_info):
        """Test system configuration in dry-run mode."""
        mock_platform.return_value = 'Darwin'
        
        with patch('provision.macos.enable_screen_sharing') as mock_screen_sharing, \
             patch('provision.macos.configure_power_management') as mock_power_mgmt:
            
            from provision.steps import configure_system
            configure_system(dry_run=True, user_only=False)
            
            # Should call both with dry_run=True
            mock_screen_sharing.assert_called_once_with(dry_run=True)
            mock_power_mgmt.assert_called_once_with(dry_run=True)
    
    @patch('provision.steps.log_info')
    @patch('provision.steps.platform.system')
    def test_configure_system_macos_user_only(self, mock_platform, mock_log_info):
        """Test system configuration in user-only mode (skips root operations)."""
        mock_platform.return_value = 'Darwin'
        
        with patch('provision.macos.enable_screen_sharing') as mock_screen_sharing, \
             patch('provision.macos.configure_power_management') as mock_power_mgmt:
            
            from provision.steps import configure_system
            configure_system(dry_run=False, user_only=True)
            
            # Should skip all system functions (they all require root)
            mock_screen_sharing.assert_not_called()
            mock_power_mgmt.assert_not_called()
            
            # Should log that we're skipping
            assert any("Skipping system configuration" in str(call) for call in mock_log_info.call_args_list)


class TestSystemVerification:
    """Tests for system verification phase."""
    
    @patch('provision.steps.log_info')
    @patch('provision.steps.platform.system')
    def test_verify_system_macos(self, mock_platform, mock_log_info):
        """Test system verification on macOS."""
        mock_platform.return_value = 'Darwin'
        
        with patch('provision.macos.verify_docker_stack') as mock_docker_verify, \
             patch('provision.macos.verify_tailscale_connectivity') as mock_tailscale_verify:
            
            mock_tailscale_verify.return_value = True  # Tailscale is connected
            
            from provision.steps import verify_system
            verify_system()
            
            # Should call both verification functions
            mock_docker_verify.assert_called_once()
            mock_tailscale_verify.assert_called_once()
    
    @patch('provision.steps.log_info')
    @patch('provision.steps.platform.system')
    def test_verify_system_unsupported_platform(self, mock_platform, mock_log_info):
        """Test system verification on unsupported platform."""
        mock_platform.return_value = 'Linux'
        
        from provision.steps import verify_system
        with pytest.raises(NotImplementedError, match="Platform Linux is not supported yet"):
            verify_system()