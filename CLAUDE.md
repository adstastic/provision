# CLAUDE.md

This repo contains `mm`, a lean Mac Mini management CLI.

## Durable intent

- Secure access is paramount.
- Required access path: Tailscale network + SSH/mosh.
- Tailscale SSH is intentionally not used.
- `mm status` is read-only.
- Mutating commands print a dry-run plan by default; `--apply` changes the system.
- Hardening must never disable SSH.
- Screen Sharing and GitHub runners are explicit toggles, not baseline assumptions.
- Personal iCloud Drive belongs to `adi`; `/Users/adi` should be private from `ci`.

## Development

Use `uv`.

```bash
uv run pytest -q
uv run mm status
uv run mm harden
```

Keep it boring:

- stdlib before dependencies
- command plans before shell blobs
- tests assert behavior/policy, not mocked internals
- delete stale provisioning paths instead of preserving parallel truths

## Slow-layer rule

Security, remote access, and user isolation changes need:

1. Phoenix claim/boundary/oracle in `.phoenix/graph.md`
2. tests for command plans or parsers
3. dry-run output before `--apply`
