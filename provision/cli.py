"""`mm` — tiny Mac Mini management CLI."""
from __future__ import annotations

import argparse
import sys
from typing import Sequence

from . import macos


def parser() -> argparse.ArgumentParser:
    formatter = argparse.RawDescriptionHelpFormatter
    p = argparse.ArgumentParser(
        prog="mm",
        description="Mac Mini management CLI. Default is dry-run; --apply mutates system.",
        epilog="""examples:
  mm status
  mm harden --keep-screen-sharing --disable-runners
  mm harden --keep-screen-sharing --disable-runners --apply
  mm screen on
  mm screen off
  mm runners off

remote safety:
  If you are not physically near the Mac, keep Screen Sharing on for first harden.
  Open two mosh sessions before --apply.
  Do not close existing sessions until a new SSH/mosh login works.
""",
        formatter_class=formatter,
    )
    p.add_argument("--apply", action="store_true", help="apply changes; default prints exact command plan")
    p.add_argument("--ssh-user", default="adi", help="local account allowed to SSH/mosh (default: adi)")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser(
        "status",
        help="show current security posture",
        description="Read-only posture check. No sudo, no changes.",
        formatter_class=formatter,
    )

    provision = sub.add_parser(
        "provision",
        help="install tools and secure baseline",
        description="Install declared packages, apply harden baseline, and keep Mac awake. Dry-run unless --apply is present.",
        formatter_class=formatter,
    )
    provision.add_argument("--with-containers", action="store_true", help="start Colima after provisioning; otherwise installed but stopped")

    harden = sub.add_parser(
        "harden",
        help="secure machine for personal iCloud/cloud-computer use",
        description="""Secure host posture while preserving SSH/mosh access.

Does:
  - keeps SSH on and key-only
  - disables Tailscale SSH
  - enables firewall + stealth
  - disables SMB/File Sharing and ARD
  - stops/blocks VibeTunnel and LM Studio ingress
  - makes /Users/<ssh-user> private
  - disables Screen Sharing unless --keep-screen-sharing
  - optionally disables GitHub Actions runners
  - runs a post-harden gate: mosh exists, SSH reachable on tailnet, blocked ports closed

Remote use:
  Use --keep-screen-sharing for first remote apply.
  Run dry-run first. Keep current mosh session open.
""",
        formatter_class=formatter,
    )
    harden.add_argument("--keep-screen-sharing", action="store_true", help="keep/enable Screen Sharing as fallback access")
    harden.add_argument("--disable-runners", action="store_true", help="disable GitHub Actions runner daemons")

    screen = sub.add_parser(
        "screen",
        help="manage Screen Sharing",
        description="Explicitly enable, disable, or inspect Screen Sharing. Use only when GUI fallback is needed.",
        formatter_class=formatter,
    )
    screen.add_argument("state", choices=("on", "off", "status"), help="desired Screen Sharing state")

    runners = sub.add_parser(
        "runners",
        help="manage GitHub Actions runner daemons",
        description="Explicitly enable, disable, or inspect self-hosted GitHub Actions runners.",
        formatter_class=formatter,
    )
    runners.add_argument("state", choices=("on", "off", "status"), help="desired runner state")

    return p


def main(argv: Sequence[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    apply = "--apply" in raw
    raw = [arg for arg in raw if arg != "--apply"]
    args = parser().parse_args(raw)
    args.apply = apply

    if args.command == "status":
        macos.print_checks(macos.status_checks(user=args.ssh_user))
        return 0

    if args.command == "provision":
        plan = macos.provision_plan(ssh_user=args.ssh_user, with_containers=args.with_containers)
    elif args.command == "harden":
        plan = macos.harden_plan(
            ssh_user=args.ssh_user,
            keep_screen_sharing=args.keep_screen_sharing,
            disable_runners=args.disable_runners,
        )
    elif args.command == "screen":
        if args.state == "status":
            macos.print_checks(c for c in macos.status_checks(user=args.ssh_user) if c.name.startswith("Screen Sharing"))
            return 0
        plan = macos.screen_sharing_plan(args.state == "on")
    elif args.command == "runners":
        if args.state == "status":
            macos.print_checks(c for c in macos.status_checks(user=args.ssh_user) if c.name == "GitHub runners")
            return 0
        plan = macos.runner_plan(args.state == "on")
    else:  # pragma: no cover - argparse prevents this
        raise AssertionError(args.command)

    if not args.apply:
        print("# dry run; re-run with --apply to change system")
    macos.run_plan(plan, dry_run=not args.apply)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
