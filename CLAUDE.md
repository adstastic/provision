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

### Python Development with uv
Always use `uv` for Python operations in this repository. uv is an extremely fast Python package and project manager written in Rust.

#### Common uv Commands:
```bash
# Run a Python script or command
uv run python script.py
uv run pytest tests/

# Initialize a new Python project
uv init

# Add dependencies to a project
uv add pytest typer sh

# Remove dependencies
uv remove package-name

# Sync project dependencies (install from pyproject.toml/uv.lock)
uv sync

# Create/update lockfile
uv lock

# For legacy requirements.txt workflows (use sparingly):
uv pip install -r requirements.txt
uv pip install -e .
```

#### Key Points:
- Prefer native uv commands (`uv add`, `uv sync`) over `uv pip`
- Always use `uv run` to execute Python scripts and commands
- uv automatically manages virtual environments
- uv is 10-100x faster than pip

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

## Development Approach

### Test-Driven Development (TDD)
This project follows strict TDD practices:
1. Write tests first (red phase)
2. Write minimal code to pass tests (green phase)
3. Refactor if needed (refactor phase)
4. Commit after each phase/feature is complete

### Git Workflow
- Make commits after completing each phase of the shell script port
- Use descriptive commit messages: `✅ Add [component]: [description]`
- Examples:
  - `✅ Add foundation: utils and CLI structure with tests`
  - `✅ Add Homebrew: package installation with tests`

### Architecture Decisions
- Keep it minimal - avoid over-abstraction
- Separate platform-specific code (macos.py, linux.py)
- Use simple function delegation instead of classes/inheritance
- Separate root and non-root operations clearly

### Testing Strategy
- Use pytest with pytest-mock for mocking system commands
- Mock all external commands (sh library calls)
- Test idempotency - functions should handle already-configured states
- Organize tests by functionality:
  - test_utils.py - Core utilities
  - test_cli.py - CLI interface
  - test_macos.py - macOS-specific implementations
  - test_steps.py - Workflow orchestration

### Learnings from Implementation

#### Typer CLI Design
- For single-command CLIs, use `invoke_without_command=True` and `callback=` instead of `@app.command()`
- This creates a cleaner UX where users run `provision` instead of `provision setup`
- Typer passes arguments as positional args, not kwargs - test assertions must match

#### Python Project Structure with uv
- Use `uv init --lib --name <name>` to create a library project
- Add dependencies with `uv add` (not `uv pip install`)
- Define CLI entry points in `pyproject.toml` under `[project.scripts]`
- Always use `uv run` to execute commands in the project environment

#### TDD Workflow
1. Write failing tests first
2. Implement minimal code to pass
3. Run tests with `uv run pytest -v`
4. Refactor if needed
5. Commit when feature is complete

#### Module Organization
- Keep `__init__.py` minimal
- Each module should have a clear, single responsibility
- Use simple functions over classes for straightforward operations
- Import order: stdlib, third-party, local modules

### Development Workflow

#### Module-by-Module TDD Process
Follow this process for each module/feature:
1. Write failing tests first (red phase)
2. Run tests to verify they fail
3. Implement minimal code to pass tests (green phase)
4. Run tests to verify they pass
5. Refactor if needed (refactor phase)
6. Commit with descriptive message
7. Update BACKLOG.md with progress
8. Update CLAUDE.md with any learnings

#### Documentation Updates
After each task completion:
- **BACKLOG.md**: Mark completed items, add any new discovered tasks
- **CLAUDE.md**: Document learnings, patterns, or gotchas discovered during implementation

This ensures knowledge is captured immediately while context is fresh.

### Learnings from Dependency Installation Phase

#### Mocking Imports in Tests
When testing functions that import modules inside them (dynamic imports), mock the actual module path, not where it's imported:
```python
# Wrong - won't work for dynamic imports
@patch('provision.steps.install_homebrew')

# Correct - mocks the actual module
@patch('provision.macos.install_homebrew')
```

#### Platform-Specific Code Organization
- Keep platform detection in the orchestration layer (steps.py)
- Import platform-specific functions dynamically to avoid import errors on other platforms
- This allows the code to run on any platform while only importing what's needed

#### Test Organization
- Group related tests into classes (TestHomebrewCheck, TestHomebrewInstallation, etc.)
- Write integration tests separately from unit tests
- Test both success paths and edge cases (dry-run, user-only mode)

#### Shell Command Execution with sh
The sh library provides a clean interface for shell commands:
```python
sh.brew("bundle", f"--file={brewfile_path}")  # Runs: brew bundle --file=/path/to/Brewfile
sh.curl("-fsSL", "https://...")  # Runs: curl -fsSL https://...
sh.go("install", "package@version")  # Runs: go install package@version
```

**Important**: sh dynamically creates command attributes based on what's in PATH. When testing:
- Mock the entire sh module: `with patch('provision.macos.sh') as mock_sh:`
- Then mock specific commands: `mock_sh.go.return_value = "output"`
- Use `@patch.dict` for os.environ: `@patch.dict('provision.macos.os.environ', {'PATH': '/usr/bin'})`
- sh raises various ErrorReturnCode_X exceptions, catch with generic `Exception`

### Learnings from Tailscale Setup Phase

#### System Daemon Management
- Use `Path.exists()` to check for LaunchDaemon plist files
- The daemon plist path is `/Library/LaunchDaemons/com.tailscale.tailscaled.plist`
- Install daemon with: `sudo tailscaled install-system-daemon`

#### DNS Configuration on macOS
- Use `networksetup` command for DNS management
- List interfaces: `networksetup -listallhardwareports`
- Get DNS servers: `networksetup -getdnsservers <interface>`
- Set DNS servers: `sudo networksetup -setdnsservers <interface> <dns1> <dns2> ...`
- Tailscale MagicDNS IP is `100.100.100.100`
- Always prepend Tailscale DNS to existing DNS servers for fallback

#### Testing Patterns for System Commands
- When mocking `sh.networksetup` with `side_effect`, provide responses in order
- Mock `sh.sudo.networksetup` separately from `sh.networksetup` for privileged commands
- Use `call` from unittest.mock to verify complex command sequences

### Learnings from Service Configuration Phase

#### LaunchAgent Management
- User-level services use LaunchAgents in `~/Library/LaunchAgents/`
- Always run LaunchAgent operations as the real user (use `sudo -u`)
- Check service status with `launchctl list`
- Load services with `launchctl load <plist>`
- Plist files should be owned by the user (`chown user:staff`)

#### Template File Management
- Store plist templates in `provision/configs/` directory
- Use string replacement for dynamic values (e.g., `TMUX_PATH_PLACEHOLDER`)
- Read templates with standard file operations, not package resources
- Copy templates to appropriate system locations

#### Homebrew Services
- Use `brew services list` to check service status
- Parse output line-by-line to check if specific service is "started"
- Start services with `brew services start <service>`
- Services like Colima may need time to initialize (use `time.sleep()`)

#### Testing Complex Path Operations
- For complex Path mocking, use `@patch.object(Path, 'exists')`
- Mock `side_effect` with a list of return values for sequential calls
- Simplify tests by focusing on the behavior being tested

#### Service Dependencies
- Check for tmux environment with `os.environ.get('TMUX')`
- Install `reattach-to-user-namespace` when running in tmux
- Both tmux and Colima services are user-level (not system daemons)

#### Mock Patterns for sh Library
- When mocking chained calls like `sh.brew.services.list()`:
  ```python
  mock_services = MagicMock()
  mock_services.list.return_value = "output"
  mock_brew.services = mock_services
  ```
- For dynamic command attributes, mock the entire sh module when needed

### Learnings from Security Configuration Phase

#### FileVault Management
- Use `fdesetup status` to check FileVault state
- Output contains "FileVault is On" or "FileVault is Off"
- Disable with `sudo fdesetup disable`
- Disabling FileVault is necessary for headless boot without physical login

#### SSH Service Management
- Use `systemsetup -getremotelogin` to check SSH status
- Output format: "Remote Login: On" or "Remote Login: Off"
- Disable with `sudo systemsetup -setremotelogin off`
- We disable standard SSH in favor of Tailscale SSH for better security

#### Firewall Configuration with socketfilterfw
- The socketfilterfw binary path: `/usr/libexec/ApplicationFirewall/socketfilterfw`
- Check status with `--getglobalstate`
- Enable firewall: `--setglobalstate on`
- Enable stealth mode: `--setstealthmode on`
- Allow signed apps: `--setallowsigned on`
- List apps: `--listapps`
- Add exception: `--add <path>`
- Unblock app: `--unblockapp <path>` (always call after adding)

#### Testing Patterns for Dynamic Command Paths
- For commands with full paths, use `getattr(sh.sudo, path)`:
  ```python
  socketfilter = getattr(sh.sudo, SOCKET_FILTER)
  socketfilter("--getglobalstate")
  ```
- In tests, mock with `setattr`:
  ```python
  mock_socketfilter = MagicMock()
  setattr(mock_sudo, '/usr/libexec/ApplicationFirewall/socketfilterfw', mock_socketfilter)
  ```

#### Security Configuration Architecture
- All security functions require root access
- In user-only mode, skip the entire security configuration phase
- Group related security settings together for clarity
- Always check current state before making changes (idempotency)

### Learnings from System Configuration Phase

#### Screen Sharing Management
- Use `launchctl list` to check if Screen Sharing service is loaded
- The service name is `com.apple.screensharing`
- Enable with: `sudo launchctl load -w /System/Library/LaunchDaemons/com.apple.screensharing.plist`
- The `-w` flag persists the setting across reboots by updating the overrides plist

#### Power Management with pmset
- Use `pmset -g` to get current power management settings
- Parse settings using regex to extract values for specific settings
- Key settings for headless servers:
  - `sleep 0` - Disable system sleep
  - `disksleep 0` - Disable disk sleep  
  - `powernap 0` - Disable Power Nap
- Use `-a` flag to apply settings for all power sources
- Always check current values before changing (idempotency)

#### Testing Patterns for System Configuration
- Mock `sh.sudo.launchctl.list()` to return service list as a string
- Mock `sh.pmset()` with appropriate side_effect for multiple calls
- For pmset output parsing, use multiline strings that match actual output format
- Test partial configuration changes to ensure only necessary changes are made

### Learnings from Verification Phase

#### Docker Stack Verification
- Check environment variable with `os.environ.get('DOCKER_HOST')`
- Verify Colima runtime status with `colima status`
- Check Docker daemon accessibility with `docker ps`
- Verify Docker Compose with `docker compose ls`
- Only check Docker commands if Colima is running to avoid misleading errors
- Provide helpful guidance when services are not running

#### Tailscale Connectivity Check
- Use `tailscale status` to check if connected
- Look for "active" in the output to determine connectivity
- Return boolean value to indicate connection status
- Provide clear instructions for manual connection if needed
- Handle exceptions gracefully when command fails

#### Sleep/Timing Considerations
- Add short sleep (2s) before Docker verification to allow services to stabilize
- This prevents false negatives when services are still initializing

#### Verification Architecture
- Keep verification functions focused and single-purpose
- Orchestrate multiple verifications in steps.py
- Don't require root access for verification phase
- Provide clear feedback about what's working and what needs attention