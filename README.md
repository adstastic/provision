# mm

Lean Mac Mini management CLI.

Goal: secure cloud-computer posture with low-friction commands. Required access is SSH/mosh over Tailscale network. Tailscale SSH is intentionally not used.

## Commands

```bash
uv run mm status                  # inspect posture, no changes
uv run mm provision               # dry-run install + secure baseline
uv run mm --apply provision       # apply install + secure baseline
uv run mm harden                  # dry-run hardening plan
uv run mm --apply harden          # SSH stays on; optional ingress shuts off
uv run mm --apply harden --keep-screen-sharing
uv run mm screen on|off|status    # explicit temporary GUI access
uv run mm runners on|off|status   # explicit GitHub runner control
```

Default is dry-run. `--apply` is required for mutation.

## Secure baseline

`mm harden` keeps:

- SSH enabled for mosh login over Tailscale
- key-only SSH after boot
- firewall + stealth mode
- mosh/Tailscale allowed through firewall
- FileVault expected on

`mm harden` disables by default:

- SMB/File Sharing
- Remote Management / ARD / Remote Apple Events
- Screen Sharing, unless `--keep-screen-sharing`

`--disable-runners` also disables GitHub Actions runner LaunchDaemons.

## iCloud rule

Personal iCloud Drive belongs to `adi`. CI/runners are treated as untrusted unless explicitly enabled. `mm harden` makes `/Users/adi` private.
