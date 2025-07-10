#!/bin/bash

# An idempotent script to configure a new macOS machine for headless server operation.
#
# This script can be run multiple times. It checks the current state of
# the system before making any changes.
#
# This script will:
# - Install Homebrew and essential tools (Go, tmux, Colima).
# - Compile and install Tailscale from source.
# - Configure Tailscale to run as a system daemon on boot.
# - Configure tmux to run as a background service.
# - Configure Colima (Docker runtime) to run as a background service.
# - Disable FileVault to allow boot without physical login.
# - Disable the standard macOS SSH server for better security.
# - Enable the macOS Firewall with Stealth Mode and configure exceptions.
# - Enable Screen Sharing (VNC) and other continuity services.
# - Disable all sleep settings to ensure the machine is always online.

set -e # Exit immediately if a command exits with a non-zero status.
set -x # Print each command before executing it for debugging

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

# Function to test if a command works correctly
test_command() {
    local name="$1"
    local test_cmd="$2"
    
    log_info "Testing $name..."
    if eval "$test_cmd" &>/dev/null; then
        log_info "$name is working correctly."
        return 0
    else
        log_action "$name test failed: $test_cmd"
        return 1
    fi
}

# --- Main Logic ---
echo "--- Starting Headless Mac Setup ---"

# --- Install Dependencies ---
log_info "Installing dependencies..."

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Install Homebrew if not present
if ! command_exists brew; then
    log_action "Homebrew not found. Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    eval "$(/opt/homebrew/bin/brew shellenv)"
else
    log_info "Homebrew is already installed."
fi

# Install all dependencies from Brewfile
log_action "Installing packages from Brewfile..."
brew bundle --file="$SCRIPT_DIR/Brewfile"

# Test installed dependencies
log_info "Testing installed dependencies..."
test_command "Go" "go version"
test_command "tmux" "tmux -V"
# Check if colima command exists
if command_exists colima; then
    log_info "Colima command is available."
else
    log_action "Colima command not found!"
fi
test_command "Docker CLI" "docker --version"

# --- Install and Configure Tailscale Daemon ---
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

# Configure DNS for Tailscale MagicDNS
log_info "Configuring DNS for Tailscale MagicDNS..."
TAILSCALE_DNS="100.100.100.100"

# Configure DNS for all network interfaces
for interface in Wi-Fi Ethernet; do
    if networksetup -listallhardwareports | grep -q "Hardware Port: $interface"; then
        if ! networksetup -getdnsservers "$interface" 2>/dev/null | grep -q "$TAILSCALE_DNS"; then
            log_action "Adding Tailscale DNS to $interface..."
            # Get current DNS servers and prepend Tailscale DNS
            CURRENT_DNS=$(networksetup -getdnsservers "$interface" 2>/dev/null | grep -v "^There aren't any" || echo "")
            sudo networksetup -setdnsservers "$interface" $TAILSCALE_DNS $CURRENT_DNS
        else
            log_info "Tailscale DNS already configured for $interface."
        fi
    fi
done

# --- Configure tmux Service ---
log_info "Setting up tmux service for user..."

# Determine the actual user running the script (even if using sudo)
if [ -n "$SUDO_USER" ]; then
    REAL_USER="$SUDO_USER"
    REAL_HOME=$(eval echo ~$SUDO_USER)
else
    REAL_USER="$USER"
    REAL_HOME="$HOME"
fi

log_info "Setting up tmux for user: $REAL_USER"

# Create LaunchAgents directory if it doesn't exist
LAUNCH_AGENTS_DIR="$REAL_HOME/Library/LaunchAgents"
if [ ! -d "$LAUNCH_AGENTS_DIR" ]; then
    log_action "Creating LaunchAgents directory..."
    sudo -u "$REAL_USER" mkdir -p "$LAUNCH_AGENTS_DIR"
fi

# Get the tmux binary path
TMUX_PATH=$(command -v tmux)
if [ -z "$TMUX_PATH" ]; then
    echo "[ERROR] Could not find tmux in PATH after installation. Exiting."
    exit 1
fi
log_info "Using tmux found at: $TMUX_PATH"

# Create tmux service plist from template
TMUX_PLIST="$LAUNCH_AGENTS_DIR/com.tmux.main.plist"
if [ ! -f "$TMUX_PLIST" ]; then
    log_action "Creating tmux service plist..."
    # Copy the template and replace the placeholder with actual tmux path
    sed "s|TMUX_PATH_PLACEHOLDER|$TMUX_PATH|g" "$SCRIPT_DIR/configs/com.tmux.main.plist" | sudo -u "$REAL_USER" tee "$TMUX_PLIST" > /dev/null
else
    log_info "tmux service plist already exists."
fi

# Load the service as the real user only if not running as root
if [ "$REAL_USER" != "root" ]; then
    if ! sudo -u "$REAL_USER" launchctl list | grep -q "com.tmux.main"; then
        log_action "Loading tmux service..."
        if sudo -u "$REAL_USER" launchctl load "$TMUX_PLIST" 2>&1; then
            log_info "tmux service loaded successfully."
        else
            log_action "Failed to load tmux service. Check logs for details."
        fi
    else
        log_info "tmux service is already loaded."
    fi
else
    log_info "Skipping tmux service for root user."
fi

# --- Configure Colima Service ---
log_info "Setting up Colima service..."

# Use Homebrew services to manage Colima
if [ "$REAL_USER" != "root" ]; then
    # Check if we're in tmux and need reattach-to-user-namespace
    if [ -n "$TMUX" ] && ! command_exists reattach-to-user-namespace; then
        log_action "Installing reattach-to-user-namespace for tmux compatibility..."
        brew install reattach-to-user-namespace
    fi
    
    # Check if Colima service is already started
    if ! brew services list | grep -q "colima.*started"; then
        log_action "Starting Colima service via Homebrew services..."
        if brew services start colima; then
            log_info "Colima service started successfully."
            # Wait a bit for Colima to fully initialize
            sleep 5
            # Verify Colima is actually running
            if colima status &>/dev/null; then
                log_info "Colima is running."
            else
                log_action "WARNING: Colima service started but Colima is not yet ready."
                log_action "It may take a moment to fully initialize."
            fi
        else
            log_action "Failed to start Colima service."
        fi
    else
        log_info "Colima service is already started."
        # But check if it's actually running
        if ! colima status &>/dev/null; then
            log_action "WARNING: Colima service is started but Colima is not running."
            log_action "Try 'brew services restart colima' to restart it."
        fi
    fi
else
    log_info "Skipping Colima service for root user."
fi

# --- Configure System Security and Access ---
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

# --- Disable All Sleep Settings ---
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

# --- Verify Docker Stack ---
log_info "Verifying Docker stack..."
# Wait a moment for Colima to start if it was just loaded
sleep 2

# Check if DOCKER_HOST is configured
if [ -z "$DOCKER_HOST" ]; then
    log_action "DOCKER_HOST is not set. Please configure your shell as shown at the end of this script."
else
    log_info "DOCKER_HOST is set to: $DOCKER_HOST"
fi

# Check if Colima is actually running
if colima status &>/dev/null; then
    log_info "Colima runtime is running."
    # Only test Docker if Colima is running
    if docker ps &>/dev/null; then
        log_info "Docker daemon is accessible."
    else
        log_action "Docker daemon is not accessible. Check DOCKER_HOST and Colima status."
    fi
    if docker compose ls &>/dev/null; then
        log_info "Docker Compose is working."
    else
        log_action "Docker Compose is not working properly."
    fi
else
    log_action "Colima is not running. Docker commands will fail until Colima is started."
    log_action "The LaunchAgent may have failed to start Colima automatically."
    log_action "Try running 'colima start' manually to start the Docker runtime."
fi

# --- Finalize Tailscale Connection ---
echo "\n--- Setup Complete ---"
log_info "Verifying Tailscale connectivity..."
if ! tailscale status | grep -q "active"; then
    echo "Tailscale is not connected. The final step is to connect to your Tailnet."
    echo "Please run the following command and follow the authentication link:"
    echo "\n    sudo tailscale up\n"
else
    log_info "Tailscale is already active."
fi

# --- Shell Configuration ---
echo "\n--- Shell Configuration Required ---"
echo "Add the following lines to your ~/.zshrc file:"
echo ""
echo "# Colima Docker configuration"
echo "export DOCKER_HOST=\"unix://\$HOME/.colima/default/docker.sock\""
echo ""
echo "# Homebrew PATH (if not already present)"
echo "eval \"\$(/opt/homebrew/bin/brew shellenv)\""
echo ""
echo "After adding these lines, run:"
echo "  source ~/.zshrc"
echo ""
echo "Then re-run this script to verify everything is configured correctly:"
echo "  $0"

