# Headless macOS Setup

Configure a macOS machine for headless server operation.

## What it does
- Installs Dependencies: Homebrew, Go, tmux, and Colima.
- Installs Tailscale: Compiles tailscale and the tailscaled daemon from source.
- Configures for Headless Boot:
  - Disables FileVault to allow unattended reboots.
  - Configures tailscaled to run as a system daemon.
  - Configures tmux to run as a background service with a persistent "main" session.
  - Configures Colima (Docker runtime) to run as a background service.
- Hardens Security:
  - Disables the standard macOS SSH server (Remote Login).
  - Enables the macOS Firewall with Stealth Mode.
  - Adds firewall exceptions for Tailscale, Screen Sharing, and Apple Continuity services.
- Enables Remote GUI Access: Ensures the Screen Sharing (VNC) service is running.
- Prevents Sleep: Disables all system and disk sleep settings.

## Prerequisites

A Mac with a fresh installation of macOS.

Physical access with a monitor and keyboard for the initial setup and user account creation.

## Usage

Clone this repository to the target machine:
```
git clone https://github.com/adstastic/provision.git
cd provision/macos
sudo provision.sh
sudo tailscale up
```

Your Mac is now configured for headless operation.
The setup script is idempotent, so can be run repeatedly to check if the system is configured properly.
