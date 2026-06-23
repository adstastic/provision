# Phoenix Graph

Core invariant: important Claims are owned by Boundaries, checked by Oracles, realized by Renderings, and supported by Evidence/provenance.

## Claims

### CLAIM-ACCESS-001

Statement: Required remote access to the Mac Mini is Tailscale network connectivity plus SSH/mosh login; Tailscale SSH is not used.

Type:
- invariant

Durability:
- slow_layer

Source:
- conversation

Owner boundary:
- BOUNDARY-MM-001

Oracles:
- ORACLE-MM-001

Renderings:
- RENDERING-MM-001

Ambiguities:
- None.

Non-goals:
- Managing Tailscale ACLs or Tailscale SSH policy outside this host.

Provenance:
- Why this exists: access must remain secure and avoid lockout while moving away from Tailscale SSH.
- Alternatives considered: Tailscale SSH; rejected because current workflow uses mosh after joining tailnet.
- Open questions: Whether to restrict SSH listen interface below OS firewall layer.

### CLAIM-ACCESS-002

Statement: `mm harden` must never disable SSH; optional ingress such as Screen Sharing, SMB, ARD, VibeTunnel, LM Studio, and GitHub runners must be explicit or disabled/warned.

Type:
- behavior

Durability:
- slow_layer

Source:
- conversation

Owner boundary:
- BOUNDARY-MM-001

Oracles:
- ORACLE-MM-001

Renderings:
- RENDERING-MM-001

Ambiguities:
- LM Studio and VibeTunnel app-specific configuration is reported by status today; full app preference management is not yet owned.

Non-goals:
- Deleting user apps without an explicit command.

Provenance:
- Why this exists: personal iCloud Drive increases blast radius of any `adi` process exposed to the network.
- Alternatives considered: leave Screen Sharing always on; rejected as baseline because it should be selectively enabled.
- Open questions: Whether Screen Sharing should be tailnet-only via packet filter.

### CLAIM-ISOLATION-001

Statement: Personal iCloud Drive belongs to `adi`; CI/runners are untrusted by default and must not read `adi` home unless explicitly enabled.

Type:
- invariant

Durability:
- slow_layer

Source:
- conversation and local audit

Owner boundary:
- BOUNDARY-MM-001

Oracles:
- ORACLE-MM-001

Renderings:
- RENDERING-MM-001

Ambiguities:
- Future iOS test runner isolation model remains undecided.

Non-goals:
- Running iOS simulator inside Linux containers.

Provenance:
- Why this exists: GitHub Actions runner compromise should not expose personal iCloud data.
- Alternatives considered: keep always-on self-hosted runners; acceptable only if isolated and trusted.
- Open questions: Whether to remove runners entirely or keep disabled until needed.

## Boundaries

### BOUNDARY-MM-001

Name: `mm` Mac Mini posture boundary

Purpose: Own host-local provisioning, hardening, status checks, and temporary feature toggles for one personal Mac Mini.

Owns claims:
- CLAIM-ACCESS-001
- CLAIM-ACCESS-002
- CLAIM-ISOLATION-001

Does not own:
- Tailscale tailnet ACLs
- App-specific internals for LM Studio/VibeTunnel beyond status/warnings unless explicit commands are added
- GitHub repository trust policy

Owned state:
- Host service enablement for SSH, Screen Sharing, SMB, ARD, GitHub runner LaunchDaemons
- Host firewall posture
- Local home-directory permissions relevant to `adi`/`ci`

Mutation authority:
- Only this boundary may: apply host hardening commands in this repo.
- This boundary may not: silently change access mode without dry-run visibility.

Public interface:
- CLI: `mm status`, `mm provision`, `mm harden`, `mm screen`, `mm runners`

Dependencies:
- macOS launchd/systemsetup/socketfilterfw/sharing/pmset
- Homebrew package manifest

Dependents:
- Human operator using SSH/mosh
- Future iCloud-trigger worker

Pace:
- slow

Blast radius:
- high

Recovery:
- rollback via dry-run command visibility plus explicit re-enable commands; physical access if SSH broken.

Regeneration policy:
- human_reviewed

Boundary oracles:
- ORACLE-MM-001

Current renderings:
- RENDERING-MM-001

Forbidden coupling:
- Provisioning code must not embed a second legacy shell source of truth.
- Optional access features must not be silently enabled by baseline provisioning.

Provenance:
- Why this boundary exists: host posture must be auditable before personal iCloud is attached.
- Alternatives considered: manual notes only; rejected because toggles need repeatable command plans.
- Rejected because: manual-only state drifts.

## Oracles

### ORACLE-MM-001

Name: `mm` plan/status tests

Checks claims:
- CLAIM-ACCESS-001
- CLAIM-ACCESS-002
- CLAIM-ISOLATION-001

Boundary:
- BOUNDARY-MM-001

Kind:
- example_test
- static_check

Durability:
- durable
- release_gate

What it checks:
- Hardening plan keeps SSH before disabling optional ingress.
- Hardening plan disables SMB/ARD/Screen Sharing by default.
- `--keep-screen-sharing` preserves Screen Sharing.
- Runner toggles are explicit.
- Tailscale SSH status JSON is parsed as a warning condition.
- Post-harden gate fails if Tailscale SSH remains enabled, mosh is missing, SSH is unreachable on tailnet, or forbidden ingress ports remain open.

What it does not check:
- Real macOS service success on every OS release.
- Tailscale ACL correctness.
- App-specific LM Studio/VibeTunnel preference files.

Pass criteria:
- `uv run pytest -q` passes.

Failure action:
- block merge

Renderings evaluated:
- RENDERING-MM-001

Evidence emitted:
- EVIDENCE-MM-001

Location:
- `tests/`

Provenance:
- Why this oracle exists: security posture is too risky to trust ad-hoc shell edits.
- Incidents/regressions covered: stale provisioning code enabling unwanted ingress; accidental SSH lockout; harden scripts silently succeeding while ports remain open.
- Known blind spots: live host commands may still fail due OS permissions; `mm status` is required before apply.

## Evidence

### EVIDENCE-MM-001

Oracle:
- ORACLE-MM-001

Supports or invalidates claims:
- CLAIM-ACCESS-001
- CLAIM-ACCESS-002
- CLAIM-ISOLATION-001

Observed rendering:
- RENDERING-MM-001

Source:
- test run

Window / sample:
- local repo after rewrite

Observed value:
- `13 passed in 0.01s`
- `python3 -m compileall -q provision` passed
- blocker-only review: no blockers
- ponytail review cut unused `Check.ok` and one-use `Runner` class

Threshold / expectation:
- all tests pass

Result:
- pass

Freshness:
- one_time

Invalidation target:
- RENDERING-MM-001

Provenance:
- Run command / dashboard / conversation / session: `uv run pytest -q`
- Notes: update after running tests.

## Renderings

### RENDERING-MM-001

Name: stdlib `mm` CLI rewrite

Boundary:
- BOUNDARY-MM-001

Realizes claims:
- CLAIM-ACCESS-001
- CLAIM-ACCESS-002
- CLAIM-ISOLATION-001

Evaluated by oracles:
- ORACLE-MM-001

Location:
- `provision/cli.py`
- `provision/macos.py`
- `macos/Brewfile`
- `README.md`

Mode:
- regenerate

Pace:
- slow

Rollback:
- git revert; old remote services can be manually re-enabled with launchctl/system settings if needed.

Generated from:
- Phoenix claims plus local system audit.

Current status:
- active

Provenance:
- Change reason: replace stale shell/Python split with one auditable CLI for secure Mac Mini management.
- Alternatives considered: patch old script; rejected due duplicated stale truth and over-mocked tests.
- Hidden claims discovered: FileVault stays on; SSH stays on; Screen Sharing optional; CI untrusted by default.
- Oracle results / Evidence: `uv run pytest -q` passed (13 tests); compileall passed; blocker-only review found no blockers; ponytail cut one-use runner wrapper.
- Human review: user requested rewrite; blocker-only reviewer found no remaining code blockers after fixes.

## Open graph issues

```text
app_specific_lockdown_for_lm_studio_and_vibetunnel
future_ios_runner_isolation_model
live_status_before_first_apply
```
