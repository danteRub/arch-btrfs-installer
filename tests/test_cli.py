import json
from pathlib import Path

import pytest

from ai_advisor.__main__ import main


FIXTURES = Path(__file__).parent / "fixtures"


def test_cli_renders_markdown_plan(capsys) -> None:
    exit_code = main([str(FIXTURES / "uefi_nvme_amd.json")])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "# Arch Btrfs AI Advisor" in captured.out
    assert "UEFI" in captured.out
    assert "amd-ucode" in captured.out
    assert "./01-installer.sh" in captured.out
    assert "critical" in captured.out


def test_cli_can_emit_json_plan(capsys) -> None:
    exit_code = main([str(FIXTURES / "uefi_nvme_amd.json"), "--json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert "UEFI" in payload["summary"]
    assert any(step["command"]["risk"] == "critical" for step in payload["steps"] if step["command"])


def test_cli_dualboot_fixture_includes_windows_warning(capsys) -> None:
    exit_code = main([str(FIXTURES / "uefi_windows_dualboot.json")])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Windows" in captured.out
    assert "Do not wipe" in captured.out


def test_cli_writes_markdown_output_file(tmp_path, capsys) -> None:
    output = tmp_path / "plans" / "plan.md"

    exit_code = main([str(FIXTURES / "uefi_nvme_amd.json"), "--output", str(output)])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == ""
    assert output.exists()
    assert "# Arch Btrfs AI Advisor" in output.read_text(encoding="utf-8")


def test_cli_writes_json_output_file(tmp_path, capsys) -> None:
    output = tmp_path / "plan.json"

    exit_code = main([str(FIXTURES / "uefi_nvme_amd.json"), "--json", "--output", str(output)])

    captured = capsys.readouterr()
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert captured.out == ""
    assert "UEFI" in payload["summary"]


def test_cli_strict_returns_2_when_warnings_exist(capsys) -> None:
    exit_code = main([str(FIXTURES / "uefi_windows_dualboot.json"), "--strict"])

    captured = capsys.readouterr()

    assert exit_code == 2
    assert "Windows" in captured.out


def test_cli_fail_on_critical_returns_3_when_critical_commands_exist(capsys) -> None:
    exit_code = main([str(FIXTURES / "uefi_nvme_amd.json"), "--fail-on-critical"])

    captured = capsys.readouterr()

    assert exit_code == 3
    assert "critical" in captured.out


def test_cli_fail_on_critical_takes_precedence_over_strict(capsys) -> None:
    exit_code = main([
        str(FIXTURES / "uefi_windows_dualboot.json"),
        "--strict",
        "--fail-on-critical",
    ])

    assert exit_code == 3


def test_cli_explain_mode_renders_explanation(capsys) -> None:
    exit_code = main([str(FIXTURES / "uefi_nvme_amd.json"), "--explain"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "# Plan explanation" in captured.out
    assert "Human review checklist" in captured.out
    assert "./01-installer.sh" in captured.out


def test_cli_explain_mode_can_write_output_file(tmp_path, capsys) -> None:
    output = tmp_path / "explanation.md"

    exit_code = main([str(FIXTURES / "uefi_nvme_amd.json"), "--explain", "--output", str(output)])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == ""
    assert "# Plan explanation" in output.read_text(encoding="utf-8")


def test_cli_json_and_explain_are_mutually_exclusive() -> None:
    with pytest.raises(SystemExit, match="--json and --explain cannot be used together"):
        main([str(FIXTURES / "uefi_nvme_amd.json"), "--json", "--explain"])
