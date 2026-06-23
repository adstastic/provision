from provision import cli


def test_help_shows_core_commands_and_remote_safety(capsys):
    try:
        cli.main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0

    out = capsys.readouterr().out
    assert "status" in out
    assert "harden" in out
    assert "screen" in out
    assert "runners" in out
    assert "Default is dry-run" in out
    assert "Open two mosh sessions" in out


def test_harden_help_shows_exact_scope_and_safety(capsys):
    try:
        cli.main(["harden", "--help"])
    except SystemExit as exc:
        assert exc.code == 0

    out = capsys.readouterr().out
    assert "keeps SSH on" in out
    assert "disables Tailscale SSH" in out
    assert "post-harden gate" in out
    assert "--keep-screen-sharing" in out


def test_harden_defaults_to_dry_run(monkeypatch, capsys):
    calls = []

    def fake_run_plan(plan, *, dry_run):
        calls.append((dry_run, list(plan)))

    monkeypatch.setattr(cli.macos, "run_plan", fake_run_plan)
    cli.main(["harden"])

    assert calls[0][0] is True
    assert "dry run" in capsys.readouterr().out


def test_apply_turns_off_dry_run_before_or_after_subcommand(monkeypatch):
    calls = []

    def fake_run_plan(plan, *, dry_run):
        calls.append(dry_run)

    monkeypatch.setattr(cli.macos, "run_plan", fake_run_plan)
    cli.main(["--apply", "screen", "off"])
    cli.main(["screen", "off", "--apply"])

    assert calls == [False, False]


def test_status_is_read_only(monkeypatch):
    calls = []
    monkeypatch.setattr(cli.macos, "status_checks", lambda user: calls.append(user) or [])
    monkeypatch.setattr(cli.macos, "print_checks", lambda checks: None)

    cli.main(["--ssh-user", "adi", "status"])

    assert calls == ["adi"]
