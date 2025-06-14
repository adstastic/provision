#!/bin/bash

# An idempotent script to configure a new macOS machine for headless server operation.
#
# This script can be run multiple times. It checks the current state of
# the system before making any changes.
#
# This script will:
# 1. Install Homebrew and essential tools (Go).
# 2. Compile and install Tailscale from source.
# 3. Configure Tailscale to run as a system daemon on boot.
# 4. Disable FileVault to allow boot without physical login.
# 5. Disable the standard macOS SSH server for better security.
# 6. Enable the macOS Firewall with Stealth Mode and configure exceptions.
# 7. Enable Screen Sharing (VNC) and other continuity services.
# 8. Disable all sleep settings to ensure the machine is always online.

set -e # Exit immediately if a command exits with a non-zero status.

# --- Helper Functions ---
# Function to check if a command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Function for consistent logging
log_info() {
    echo "[INFO] $1"
}

log_action() {
    echo "  -> $1"
}

# --- Main Logic ---
echo "--- Starting Headless Mac Setup ---"

# --- Step 1: Install Dependencies ---
log_info "Checking dependencies..."
if ! command_exists brew; then
    log_action "Homebrew not found. Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    eval "$(/opt/homebrew/bin/brew shellenv)"
else
    log_info "Homebrew is already installed."
fi

if ! command_exists go; then
    log_action "Go not found. Installing Go via Homebrew..."
    brew install go
else
    log_info "Go is already installed."
fi

# --- Step 2: Install and Configure Tailscale Daemon ---
log_info "Checking Tailscale installation..."
if ! command_exists tailscaled; then
    log_action "tailscaled not found. Installing Tailscale from source..."
    # This command installs both tailscale and tailscaled
    export PATH=$PATH:$(go env GOPATH)/bin
    go install tailscale.com/cmd/tailscale{,d}@main
else
    log_info "Tailscale appears to be installed."
fi

# Dynamically find the path to the tailscaled binary
TAILSCALED_PATH=$(command -v tailscaled)
if [ -z "$TAILSCALED_PATH" ]; then
    echo "[ERROR] Could not find tailscaled in PATH after installation. Exiting."
    exit 1
fi
log_info "Using tailscaled found at: $TAILSCALED_PATH"


log_info "Checking Tailscale system daemon..."
DAEMON_PLIST="/Library/LaunchDaemons/com.tailscale.tailscaled.plist"
if [ ! -f "$DAEMON_PLIST" ]; then
    log_action "Tailscale system daemon not found. Installing..."
    sudo "$TAILSCALED_PATH" install-system-daemon
else
    log_info "Tailscale system daemon is already installed."
fi

# --- Step 3: Configure System Security and Access ---
log_info "Checking security settings..."

# FileVault Check
if sudo fdesetup status | grep -q "FileVault is On."; then
    log_action "FileVault is enabled. Disabling for headless boot..."
    sudo fdesetup disable
else
    log_info "FileVault is already disabled."
fi

# Remote Login (SSH) Check
if sudo systemsetup -getremotelogin | grep -q "On"; then
    log_action "Standard SSH (Remote Login) is enabled. Disabling..."
    sudo systemsetup -setremotelogin off
else
    log_info "Standard SSH (Remote Login) is already disabled."
fi

# Firewall Check
SOCKET_FILTER="/usr/libexec/ApplicationFirewall/socketfilterfw"
if ! sudo "$SOCKET_FILTER" --getglobalstate | grep -q "enabled"; then
    log_action "Firewall is disabled. Enabling firewall..."
    sudo "$SOCKET_FILTER" --setglobalstate on
    sudo "$SOCKET_FILTER" --setallowsigned on
    sudo "$SOCKET_FILTER" --setstealthmode on
else
    log_info "Firewall is already enabled."
fi

# Firewall Rules Check
log_info "Verifying firewall exceptions for continuity services..."
SERVICES_TO_CHECK=(
    "$TAILSCALED_PATH"
    "/System/Library/CoreServices/RemoteManagement/ARDAgent.app"
    "/System/Library/CoreServices/UniversalControl.app"
    "/usr/libexec/sharingd"
    "/usr/libexec/rapportd"
)

for service_path in "${SERVICES_TO_CHECK[@]}"; do
    # Using grep -F for fixed string matching is more robust
    if ! sudo "$SOCKET_FILTER" --listapps | grep -qF "$service_path"; then
        log_action "Adding firewall exception for: $service_path"
        sudo "$SOCKET_FILTER" --add "$service_path"
    fi
    # Use the correct --unblockapp flag to allow connections
    sudo "$SOCKET_FILTER" --unblockapp "$service_path"
done
log_info "Firewall exceptions are configured."

# Screen Sharing Service Check
if ! sudo launchctl list | grep -q "com.apple.screensharing"; then
    log_action "Screen Sharing service is not loaded. Enabling..."
    sudo launchctl load -w /System/Library/LaunchDaemons/com.apple.screensharing.plist
else
    log_info "Screen Sharing service is already enabled."
fi

# --- Step 4: Disable All Sleep Settings ---
log_info "Checking power management settings..."
# The grep pattern '^[[:space:]]*<setting> ' ensures we match the specific line
# for each setting, avoiding partial matches with other settings.
if [[ $(pmset -g | grep '^[[:space:]]*sleep ' | awk '{print $2}') != "0" ]]; then
    log_action "Disabling system sleep..."
    sudo pmset -a sleep 0
fi

if [[ $(pmset -g | grep '^[[:space:]]*disksleep ' | awk '{print $2}') != "0" ]]; then
    log_action "Disabling disk sleep..."
    sudo pmset -a disksleep 0
fi

if [[ $(pmset -g | grep '^[[:space:]]*powernap ' | awk '{print $2}') != "0" ]]; then
    log_action "Disabling Power Nap..."
    sudo pmset -a powernap 0
fi
log_info "Power settings configured to prevent sleep."

# --- Step 5: Finalize Tailscale Connection ---
echo "\n--- Setup Complete ---"
log_info "Verifying Tailscale connectivity..."
if ! tailscale status | grep -q "active"; then
    echo "Tailscale is not connected. The final step is to connect to your Tailnet."
    echo "Please run the following command and follow the authentication link:"
    echo "\n    sudo tailscale up\n"
else
    log_info "Tailscale is already active."
fi

