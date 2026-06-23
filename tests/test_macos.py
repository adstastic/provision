import pytest

from provision import macos


def rendered(plan):
    return "\n".join(command.render() for command in plan)


def notes(plan):
    return [command.note for command in plan]


def test_harden_keeps_ssh_before_disabling_ingress():
    plan = macos.harden_plan(ssh_user="adi")
    text = rendered(plan)

    assert "systemsetup -setremotelogin on" in text
    assert text.index("systemsetup -setremotelogin on") < text.index("com.apple.smbd")
    assert text.index("systemsetup -setremotelogin on") < text.index("com.apple.screensharing")
    assert "--ssh=false" in text
    assert "/usr/sbin/sshd -t" in text
    assert "restored previous config" in text
    assert "PasswordAuthentication no" in text
    assert "AllowUsers adi" in text
    assert "harden gate failed" in text
    assert "SSH not reachable on tailnet" in text
    assert "mosh-server unavailable" in text


def test_harden_disables_optional_ingress_by_default():
    plan = macos.harden_plan(ssh_user="adi")
    text = rendered(plan)

    assert "sharing -l -f json" in text
    assert "com.apple.smbd" in text
    assert "com.apple.netbiosd" in text
    assert "kickstart" in text
    assert "com.apple.remotemanagementd" in text
    assert "VibeTunnel.app" in text
    assert "LM Studio.app" in text
    assert "pkill -f" not in text
    assert "pkill -x" in text
    assert "for port in 4020 1234" in text
    assert "lsof -nP -tiTCP:$port" in text
    assert "com.apple.screensharing" in text
    assert "bootout system/com.apple.screensharing" in text


def test_harden_can_keep_screen_sharing_temporarily():
    plan = macos.harden_plan(ssh_user="adi", keep_screen_sharing=True)
    text = rendered(plan)

    assert "enable Screen Sharing explicitly" in notes(plan)
    assert "kickstart -k system/com.apple.screensharing" in text
    assert "bootout system/com.apple.screensharing" not in text
    gate_text = rendered([plan[-1]])
    assert "5900" not in gate_text


def test_harden_disables_runners_only_when_requested():
    default = rendered(macos.harden_plan(ssh_user="adi"))
    with_runners = rendered(macos.harden_plan(ssh_user="adi", disable_runners=True))

    assert "actions.runner.*.plist" not in default
    assert "actions.runner.*.plist" in with_runners
    assert "launchctl disable" in with_runners

    enabled = rendered(macos.runner_plan(True))
    assert "launchctl bootstrap system" in enabled


def test_screen_sharing_toggle_plans_are_explicit():
    on = rendered(macos.screen_sharing_plan(True))
    off = rendered(macos.screen_sharing_plan(False))

    assert "kickstart -k system/com.apple.screensharing" in on
    assert macos.SCREEN_SHARING_BUNDLE in on
    assert "bootout system/com.apple.screensharing" in off
    assert "--blockapp" in off


def test_firewall_plan_allows_access_tools_and_disables_auto_allow_signed():
    text = rendered(macos.firewall_plan())

    assert "--setglobalstate on" in text
    assert "--setstealthmode on" in text
    assert "--setallowsigned off" in text
    assert "/sbin/launchd" in text
    assert "mosh-server" in text
    assert "tailscaled" in text
    assert "sshd-session" in text


def test_tailscale_ssh_enabled_parser():
    assert macos.tailscale_ssh_enabled('{"Self":{"SSH_HostKeys":["ssh-ed25519 AAA"]}}') is True
    assert macos.tailscale_ssh_enabled('{"Self":{}}') is False
    assert macos.tailscale_ssh_enabled('not json') is False


def test_ssh_user_must_be_plain_account_name():
    with pytest.raises(ValueError):
        macos.harden_plan(ssh_user="adi; rm -rf /")


def test_provision_applies_secure_baseline_and_does_not_start_colima_unless_requested():
    default = rendered(macos.provision_plan(ssh_user="adi"))
    containers = rendered(macos.provision_plan(ssh_user="adi", with_containers=True))

    assert "bundle --file" in default
    assert "systemsetup -setremotelogin on" in default
    assert "--setglobalstate on" in default
    assert "sharing -l -f json" in default
    assert "bootout system/com.apple.screensharing" in default
    assert "brew services start colima" not in default
    assert "brew services start colima" in containers
