"""Mac Mini management primitives.

This module owns plans, not opinions hidden in shell glue. Mutating operations are
small command lists so dry-run and tests see the same thing apply uses.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import shlex
import socket
import stat
import subprocess
import sys
from typing import Iterable, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
BREWFILE = REPO_ROOT / "macos" / "Brewfile"
SOCKET_FILTER = "/usr/libexec/ApplicationFirewall/socketfilterfw"
SCREEN_SHARING_PLIST = "/System/Library/LaunchDaemons/com.apple.screensharing.plist"
SCREEN_SHARING_BUNDLE = "/System/Library/CoreServices/RemoteManagement/screensharingd.bundle"
ARD_KICKSTART = "/System/Library/CoreServices/RemoteManagement/ARDAgent.app/Contents/Resources/kickstart"

SSH_HARDENING_TEMPLATE = """# Managed by mm. Keep SSH for mosh over Tailscale; do not use Tailscale SSH.
PubkeyAuthentication yes
AuthenticationMethods publickey
PasswordAuthentication no
KbdInteractiveAuthentication no
ChallengeResponseAuthentication no
PermitRootLogin no
AllowUsers {ssh_user}
X11Forwarding no
AllowAgentForwarding no
PermitTunnel no
GatewayPorts no
PermitUserEnvironment no
MaxAuthTries 3
LoginGraceTime 30
MaxSessions 10
LogLevel VERBOSE
"""


@dataclass(frozen=True)
class Command:
    """One command in a management plan."""

    args: tuple[str, ...]
    sudo: bool = False
    note: str = ""

    def argv(self) -> list[str]:
        if self.sudo:
            return ["sudo", *self.args]
        return list(self.args)

    def render(self) -> str:
        return " ".join(shlex.quote(part) for part in self.argv())


@dataclass(frozen=True)
class Check:
    name: str
    state: str
    detail: str = ""


def run_plan(commands: Iterable[Command], *, dry_run: bool = True) -> None:
    commands = list(commands)
    if not dry_run and any(command.sudo for command in commands):
        try:
            subprocess.run(["sudo", "-v"], check=True)
        except subprocess.CalledProcessError as exc:
            print("sudo authentication failed; run --apply from an interactive SSH/mosh shell", file=sys.stderr)
            raise SystemExit(exc.returncode) from exc
    for command in commands:
        if command.note:
            print(f"# {command.note}")
        print(f"$ {command.render()}")
        if not dry_run:
            subprocess.run(command.argv(), check=True)


def require_safe_user(user: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", user):
        raise ValueError(f"unsafe macOS account name: {user!r}")
    return user


def bash(script: str, *, sudo: bool = False, note: str = "") -> Command:
    return Command(("bash", "-lc", script), sudo=sudo, note=note)


def provision_plan(*, ssh_user: str = "adi", with_containers: bool = False) -> list[Command]:
    """Install baseline tools and apply secure baseline.

    Containers are installed by Brewfile but not auto-started unless requested.
    """
    commands = [
        bash(
            "command -v brew >/dev/null || "
            "NONINTERACTIVE=1 /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"",
            note="install Homebrew if missing",
        ),
        bash(
            f"brew=$(command -v brew || true); [ -n \"$brew\" ] || brew=/opt/homebrew/bin/brew; \"$brew\" bundle --file={shlex.quote(str(BREWFILE))}",
            note="install/update declared packages",
        ),
        *harden_plan(ssh_user=ssh_user),
        *power_plan(),
    ]
    if with_containers:
        commands.append(Command(("brew", "services", "start", "colima"), note="start Colima only when explicitly requested"))
    return commands


def harden_plan(
    *,
    ssh_user: str = "adi",
    keep_screen_sharing: bool = False,
    disable_runners: bool = False,
) -> list[Command]:
    commands = [
        *base_security_plan(ssh_user=ssh_user),
        *firewall_plan(),
        *disable_file_sharing_plan(),
        *disable_remote_management_plan(),
        *app_ingress_plan(),
        *home_isolation_plan(ssh_user),
    ]
    if keep_screen_sharing:
        commands.extend(screen_sharing_plan(True))
    else:
        commands.extend(screen_sharing_plan(False))
    if disable_runners:
        commands.extend(runner_plan(False))
    commands.extend(post_harden_gate_plan(allow_screen_sharing=keep_screen_sharing))
    return commands


def base_security_plan(*, ssh_user: str) -> list[Command]:
    ssh_user = require_safe_user(ssh_user)
    ssh_config = SSH_HARDENING_TEMPLATE.format(ssh_user=ssh_user)
    script = f"""
set -euo pipefail
test -s /Users/{shlex.quote(ssh_user)}/.ssh/authorized_keys || {{ echo 'missing /Users/{ssh_user}/.ssh/authorized_keys'; exit 1; }}
tailscale_bin=$(command -v tailscale || true)
[ -n "$tailscale_bin" ] || [ ! -x /opt/homebrew/bin/tailscale ] || tailscale_bin=/opt/homebrew/bin/tailscale
[ -n "$tailscale_bin" ] || [ ! -x /usr/local/bin/tailscale ] || tailscale_bin=/usr/local/bin/tailscale
[ -z "$tailscale_bin" ] || "$tailscale_bin" set --ssh=false
systemsetup -setremotelogin on
install -d -m 755 /etc/ssh/sshd_config.d
target=/etc/ssh/sshd_config.d/99-mm-hardening.conf
backup="$target.bak.$(date +%s)"
tmp=$(mktemp)
[ -f "$target" ] && cp "$target" "$backup"
cat > "$tmp" <<'EOF'
{ssh_config}EOF
install -m 644 "$tmp" "$target"
rm -f "$tmp"
if ! /usr/sbin/sshd -t; then
  if [ -f "$backup" ]; then
    cp "$backup" "$target"
  else
    rm -f "$target"
  fi
  echo 'invalid sshd config; restored previous config' >&2
  exit 1
fi
launchctl enable system/com.openssh.sshd 2>/dev/null || true
launchctl kickstart -k system/com.openssh.sshd 2>/dev/null || true
""".strip()
    return [bash(script, sudo=True, note="keep SSH on, disable Tailscale SSH, validate key-only SSH config")]


def firewall_plan() -> list[Command]:
    script = f"""
set -euo pipefail
sf={shlex.quote(SOCKET_FILTER)}
"$sf" --setglobalstate on
"$sf" --setstealthmode on
"$sf" --setallowsigned off
"$sf" --setallowsignedapp off
for app in \
  /sbin/launchd \
  /usr/libexec/sshd-session \
  /usr/bin/ssh \
  /opt/homebrew/bin/mosh-server \
  /opt/homebrew/Cellar/mosh/*/bin/mosh-server \
  /Applications/Tailscale.app \
  /usr/local/bin/tailscaled \
  /opt/homebrew/opt/tailscale/bin/tailscaled; do
  for path in $app; do
    [ -e "$path" ] || continue
    "$sf" --add "$path" 2>/dev/null || true
    "$sf" --unblockapp "$path" 2>/dev/null || true
  done
done
""".strip()
    return [bash(script, sudo=True, note="firewall on; only SSH/mosh/Tailscale explicitly allowed")]


def disable_file_sharing_plan() -> list[Command]:
    script = r"""
set -euo pipefail
sharing -l -f json 2>/dev/null | python3 -c '
import json, subprocess, sys
try:
    shares = json.load(sys.stdin)
except Exception:
    shares = {}
for name in shares:
    subprocess.run(["sharing", "-r", name], check=False)
'
for label in com.apple.smbd com.apple.netbiosd; do
  launchctl disable "system/$label" 2>/dev/null || true
  launchctl bootout "system/$label" 2>/dev/null || true
done
""".strip()
    return [bash(script, sudo=True, note="disable SMB/File Sharing and remove sharepoints")]


def disable_remote_management_plan() -> list[Command]:
    script = f"""
set -euo pipefail
[ -x {shlex.quote(ARD_KICKSTART)} ] && {shlex.quote(ARD_KICKSTART)} -deactivate -stop 2>/dev/null || true
for label in com.apple.remotemanagementd com.apple.RemoteDesktop.PrivilegeProxy; do
  launchctl disable "system/$label" 2>/dev/null || true
  launchctl bootout "system/$label" 2>/dev/null || true
done
systemsetup -setremoteappleevents off 2>/dev/null || true
""".strip()
    return [bash(script, sudo=True, note="disable Remote Management / ARD / Remote Apple Events")]


def app_ingress_plan() -> list[Command]:
    script = f"""
set -euo pipefail
pkill -x 'vibetunnel' 2>/dev/null || true
pkill -x 'VibeTunnel' 2>/dev/null || true
pkill -x 'LM Studio' 2>/dev/null || true
for port in 4020 1234; do
  lsof -nP -tiTCP:$port -sTCP:LISTEN 2>/dev/null | xargs -r kill 2>/dev/null || true
done
for app in '/Applications/VibeTunnel.app' '/Applications/LM Studio.app'; do
  [ -e "$app" ] || continue
  {shlex.quote(SOCKET_FILTER)} --blockapp "$app" 2>/dev/null || true
done
""".strip()
    return [bash(script, sudo=True, note="stop/block known app ingress: VibeTunnel and LM Studio")]


def screen_sharing_plan(enable: bool) -> list[Command]:
    if enable:
        script = f"""
set -euo pipefail
launchctl enable system/com.apple.screensharing 2>/dev/null || true
launchctl bootstrap system {shlex.quote(SCREEN_SHARING_PLIST)} 2>/dev/null || true
launchctl kickstart -k system/com.apple.screensharing 2>/dev/null || true
{shlex.quote(SOCKET_FILTER)} --add {shlex.quote(SCREEN_SHARING_BUNDLE)} 2>/dev/null || true
{shlex.quote(SOCKET_FILTER)} --unblockapp {shlex.quote(SCREEN_SHARING_BUNDLE)} 2>/dev/null || true
""".strip()
        return [bash(script, sudo=True, note="enable Screen Sharing explicitly")]

    script = f"""
set -euo pipefail
launchctl disable system/com.apple.screensharing 2>/dev/null || true
launchctl bootout system/com.apple.screensharing 2>/dev/null || true
{shlex.quote(SOCKET_FILTER)} --blockapp {shlex.quote(SCREEN_SHARING_BUNDLE)} 2>/dev/null || true
""".strip()
    return [bash(script, sudo=True, note="disable Screen Sharing")]


def runner_plan(enable: bool) -> list[Command]:
    if enable:
        script = """
set -euo pipefail
shopt -s nullglob
for plist in /Library/LaunchDaemons/actions.runner.*.plist; do
  label=$(basename "$plist" .plist)
  launchctl enable "system/$label" 2>/dev/null || true
  launchctl bootstrap system "$plist" 2>/dev/null || true
  launchctl kickstart -k "system/$label" 2>/dev/null || true
done
""".strip()
        return [bash(script, sudo=True, note="enable GitHub Actions runners")]

    script = """
set -euo pipefail
shopt -s nullglob
for plist in /Library/LaunchDaemons/actions.runner.*.plist; do
  label=$(basename "$plist" .plist)
  launchctl disable "system/$label" 2>/dev/null || true
  launchctl bootout "system/$label" 2>/dev/null || true
done
""".strip()
    return [bash(script, sudo=True, note="disable GitHub Actions runners")]


def post_harden_gate_plan(*, allow_screen_sharing: bool = False) -> list[Command]:
    blocked_ports = {
        445: "SMB/File Sharing",
        3283: "ARD/Remote Management",
        4020: "VibeTunnel",
        1234: "LM Studio",
    }
    if not allow_screen_sharing:
        blocked_ports[5900] = "Screen Sharing"
    ports_json = json.dumps(blocked_ports)
    script = f"""
python3 - <<'PY'
import json, socket, subprocess, sys

blocked_ports = {{int(k): v for k, v in json.loads({ports_json!r}).items()}}

def text(cmd):
    try:
        return subprocess.run(cmd, text=True, capture_output=True, timeout=3, check=False).stdout.strip()
    except Exception:
        return ""

def tailscale_cmd():
    for candidate in ("/opt/homebrew/bin/tailscale", "/usr/local/bin/tailscale", "tailscale"):
        try:
            result = subprocess.run([candidate, "status", "--json"], text=True, capture_output=True, timeout=3, check=False)
        except Exception:
            continue
        if result.returncode == 0 and result.stdout.strip():
            return candidate, result.stdout
    return "", ""

ts_cmd, ts_status = tailscale_cmd()
if not ts_cmd:
    raise SystemExit("harden gate failed: tailscale CLI/status unavailable")
try:
    if json.loads(ts_status).get("Self", {{}}).get("SSH_HostKeys"):
        raise SystemExit("harden gate failed: Tailscale SSH still enabled")
except json.JSONDecodeError as exc:
    raise SystemExit(f"harden gate failed: invalid tailscale status JSON: {{exc}}")

mosh = text(["/usr/bin/which", "mosh-server"])
if not mosh:
    raise SystemExit("harden gate failed: mosh-server unavailable")

tail_ip = text([ts_cmd, "ip", "-4"]).splitlines()[0]
try:
    with socket.create_connection((tail_ip, 22), timeout=0.6):
        pass
except OSError as exc:
    raise SystemExit(f"harden gate failed: SSH not reachable on tailnet {{tail_ip}}:22: {{exc}}")

hosts = []
for cmd in (["ipconfig", "getifaddr", "en0"], [ts_cmd, "ip", "-4"]):
    out = text(cmd)
    if out:
        hosts.append(out.splitlines()[0])

failures = []
for host in hosts:
    for port, name in blocked_ports.items():
        try:
            with socket.create_connection((host, port), timeout=0.4):
                failures.append(f"{{name}} open on {{host}}:{{port}}")
        except OSError:
            pass

if failures:
    raise SystemExit("harden gate failed: " + "; ".join(failures))
print("harden gate passed")
PY
""".strip()
    return [bash(script, note="verify hardened ingress is closed")]


def home_isolation_plan(ssh_user: str) -> list[Command]:
    ssh_user = require_safe_user(ssh_user)
    script = f"""
set -euo pipefail
chmod 700 /Users/{shlex.quote(ssh_user)}
[ -d /Users/ci ] && chmod 700 /Users/ci || true
[ -d /Users/ci ] && find /Users/ci -maxdepth 1 -type d -name 'actions-runner-*' -exec chmod 700 {{}} \\; || true
[ -d /Users/ci ] && find /Users/ci -path '/Users/ci/actions-runner-*/*' \\( -name '.credentials*' -o -name '.runner' -o -name '.env' -o -name '.path' \\) -exec chmod 600 {{}} \\; || true
""".strip()
    return [bash(script, sudo=True, note="isolate adi home and CI runner files")]


def power_plan() -> list[Command]:
    return [
        bash(
            "pmset -a sleep 0 disksleep 0 powernap 0",
            sudo=True,
            note="keep Mac reachable",
        )
    ]


def run_text(args: Sequence[str], timeout: float = 3.0) -> str:
    try:
        return subprocess.run(args, text=True, capture_output=True, timeout=timeout, check=False).stdout.strip()
    except Exception as exc:  # command missing, timeout, permission issue
        return f"ERROR: {exc}"


def command_exists(name: str) -> bool:
    return subprocess.run(["/usr/bin/which", name], capture_output=True).returncode == 0


def port_open(host: str, port: int, timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def tailscale_ip() -> str:
    return run_text(["tailscale", "ip", "-4"]).splitlines()[0] if command_exists("tailscale") else ""


def lan_ip() -> str:
    return run_text(["ipconfig", "getifaddr", "en0"])


def tailscale_ssh_enabled(status_json: str) -> bool:
    try:
        data = json.loads(status_json)
    except json.JSONDecodeError:
        return False
    return bool(data.get("Self", {}).get("SSH_HostKeys"))


def home_mode(path: Path) -> str:
    try:
        return oct(stat.S_IMODE(path.stat().st_mode))
    except OSError:
        return "missing"


def status_checks(*, user: str = "adi") -> list[Check]:
    checks: list[Check] = []

    fv = run_text(["fdesetup", "status"])
    checks.append(Check("FileVault", "ok" if "FileVault is On" in fv else "warn", fv))

    fw = run_text([SOCKET_FILTER, "--getglobalstate"])
    checks.append(Check("Firewall", "ok" if "enabled" in fw else "fail", fw))

    stealth = run_text([SOCKET_FILTER, "--getstealthmode"])
    stealth_on = "enabled" in stealth.lower() or " is on" in stealth.lower()
    checks.append(Check("Firewall stealth", "ok" if stealth_on else "warn", stealth))

    checks.append(Check("SSH port", "ok" if port_open("127.0.0.1", 22) else "fail", "127.0.0.1:22"))
    checks.append(Check("mosh-server", "ok" if command_exists("mosh-server") else "fail", "required for mosh login"))

    ts = run_text(["tailscale", "status", "--json"]) if command_exists("tailscale") else ""
    checks.append(Check("Tailscale", "ok" if ts and not ts.startswith("ERROR") else "fail", "connected/status available"))
    checks.append(Check("Tailscale SSH", "warn" if tailscale_ssh_enabled(ts) else "ok", "must stay off; use Tailscale network + mosh"))

    mode = home_mode(Path(f"/Users/{user}"))
    checks.append(Check(f"/Users/{user} mode", "ok" if mode == "0o700" else "warn", mode))

    tail_ip = tailscale_ip()
    hosts = [h for h in (lan_ip(), tail_ip) if h and not h.startswith("ERROR")]
    for host in hosts:
        for name, port in (
            ("SMB", 445),
            ("Screen Sharing", 5900),
            ("ARD", 3283),
            ("VibeTunnel", 4020),
            ("LM Studio", 1234),
        ):
            checks.append(Check(f"{name} on {host}", "warn" if port_open(host, port) else "ok", f"port {port}"))

    runners = run_text(["pgrep", "-fl", "Runner.Listener"])
    checks.append(Check("GitHub runners", "warn" if runners else "ok", runners or "not running"))

    return checks


def print_checks(checks: Iterable[Check]) -> None:
    for check in checks:
        marker = {"ok": "OK", "warn": "WARN", "fail": "FAIL"}.get(check.state, check.state.upper())
        detail = f" — {check.detail}" if check.detail else ""
        print(f"[{marker}] {check.name}{detail}")
