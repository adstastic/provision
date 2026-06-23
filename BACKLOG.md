# BACKLOG

## Now
- [x] Replace duplicated shell/Python provisioning with one `mm` CLI
- [x] Record durable access/isolation claims in `.phoenix/graph.md`
- [x] Make mutation dry-run by default and gated by `--apply`
- [x] Add `status`, `provision`, `harden`, `screen`, and `runners` commands
- [x] Remove runtime dependencies (`typer`, `sh`, `pyyaml`)
- [x] Replace over-mocked tests with plan/policy tests

## Next
- [ ] Add `mm apps` checks/fixes for LM Studio and VibeTunnel preference-level lockdown
- [ ] Decide future iOS runner model: removed, disabled-until-needed, or isolated `ci`
- [ ] Add tailnet-only Screen Sharing enforcement if macOS packet filter rule proves reliable
- [ ] Add `mm audit` JSON output for machine-readable posture snapshots
