# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This repository contains provisioning scripts for automating the setup and hardening of macOS and Linux servers for personal infrastructure. The primary focus is creating secure, headless server configurations that can operate without physical access.

## Architecture

The codebase follows a platform-specific structure:
- `/macos/` - macOS-specific provisioning scripts
  - `provision.sh` - Main bash script that performs all configuration
  - `README.md` - Detailed documentation for macOS setup

Future directories will include Linux provisioning scripts as mentioned in the root README.

## Key Development Principles

### Idempotency
The provisioning scripts are designed to be run multiple times without causing issues. Always check system state before making changes:
```bash
if ! command_exists brew; then
    # Install Homebrew
else
    log_info "Homebrew is already installed."
fi
```

### Security-First Approach
- Disable standard SSH in favor of Tailscale SSH
- Enable firewall with stealth mode
- Use minimal necessary permissions
- Never expose secrets or sensitive configuration

### Logging Pattern
Use consistent logging functions:
- `log_info()` - General information messages
- `log_action()` - Actions being performed (indented with "->")

### Error Handling
Scripts use `set -e` to exit on errors. Ensure all commands that might fail are properly handled.

## Common Commands

### Running the Provisioning Script
```bash
cd macos
sudo ./provision.sh
```

### Testing Script Changes
Since this is a system configuration script, test changes carefully:
1. Run on a test macOS VM first if possible
2. Ensure idempotency by running the script multiple times
3. Verify each step completes successfully

### Checking Script Syntax
```bash
bash -n provision.sh  # Syntax check without execution
```

## Script Architecture

The macOS provision.sh script follows this structure:
1. Helper functions (command_exists, logging)
2. Dependency installation (Homebrew, Go)
3. Tailscale setup (compile from source, system daemon)
4. Security configuration (FileVault, SSH, Firewall)
5. Remote access setup (Screen Sharing)
6. Power management (disable sleep)

Each section checks current state before making changes to maintain idempotency.

## Important Implementation Details

### Tailscale Installation
- Compiled from source using Go rather than Homebrew package
- Installed as system daemon using `tailscaled install-system-daemon`
- Binary path is dynamically determined after installation

### Firewall Configuration
Uses `/usr/libexec/ApplicationFirewall/socketfilterfw` for firewall management:
- Enable firewall with stealth mode
- Add exceptions for required services
- Use `--unblockapp` to allow connections

### Service Management
- LaunchDaemons are used for system services
- Check service status with `launchctl list`
- Load services with `launchctl load -w`

## Configuration Management Best Practices
- Don't inline config file content. Use config files instead, and copy them to the correct locations.