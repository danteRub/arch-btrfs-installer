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
    assert "## Status" in captured.out
    assert "`needs_review`" in captured.out
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
    assert payload["status"] == "needs_review"
    assert payload["status_reasons"]
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
    contents = output.read_text(encoding="utf-8")
    assert "# Arch Btrfs AI Advisor" in contents
    assert "## Status" in contents


def test_cli_writes_json_output_file(tmp_path, capsys) -> None:
    output = tmp_path / "plan.json"

    exit_code = main([str(FIXTURES / "uefi_nvme_amd.json"), "--json", "--output", str(output)])

    captured = capsys.readouterr()
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert captured.out == ""
    assert "UEFI" in payload["summary"]
    assert payload["status"] == "needs_review"


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


def test_cli_doctor_mode_renders_health_report(capsys) -> None:
    exit_code = main([str(FIXTURES / "uefi_nvme_amd.json"), "--doctor"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "# Advisor doctor report" in captured.out
    assert "Status: `needs_review`" in captured.out
    assert "Boot mode: `UEFI`" in captured.out
    assert "Microcode package: `amd-ucode`" in captured.out
    assert "Critical commands: `1`" in captured.out


def test_cli_doctor_mode_can_write_output_file(tmp_path, capsys) -> None:
    output = tmp_path / "doctor.md"

    exit_code = main([str(FIXTURES / "uefi_windows_dualboot.json"), "--doctor", "--output", str(output)])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == ""
    contents = output.read_text(encoding="utf-8")
    assert "# Advisor doctor report" in contents
    assert "Windows/NTFS markers detected: `yes`" in contents


def test_cli_bundle_mode_writes_all_expected_files(tmp_path, capsys) -> None:
    bundle_dir = tmp_path / "bundle"

    exit_code = main([str(FIXTURES / "uefi_nvme_amd.json"), "--bundle", str(bundle_dir)])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert f"Bundle written to {bundle_dir}" in captured.out
    expected_files = {
        "system_report.json",
        "plan.md",
        "plan.json",
        "doctor.md",
        "explanation.md",
        "summary.txt",
    }
    assert expected_files == {path.name for path in bundle_dir.iterdir()}
    assert "# Arch Btrfs AI Advisor" in (bundle_dir / "plan.md").read_text(encoding="utf-8")
    assert "# Advisor doctor report" in (bundle_dir / "doctor.md").read_text(encoding="utf-8")
    assert "# Plan explanation" in (bundle_dir / "explanation.md").read_text(encoding="utf-8")
    assert "Status: needs_review" in (bundle_dir / "summary.txt").read_text(encoding="utf-8")
    assert json.loads((bundle_dir / "plan.json").read_text(encoding="utf-8"))["status"] == "needs_review"


def test_cli_bundle_mode_rejects_output(tmp_path) -> None:
    with pytest.raises(SystemExit, match="--bundle cannot be used with --output"):
        main([
            str(FIXTURES / "uefi_nvme_amd.json"),
            "--bundle",
            str(tmp_path / "bundle"),
            "--output",
            str(tmp_path / "ignored.md"),
        ])


def test_cli_modes_are_mutually_exclusive() -> None:
    with pytest.raises(SystemExit, match="--json, --explain, --doctor and --bundle are mutually exclusive"):
        main([str(FIXTURES / "uefi_nvme_amd.json"), "--json", "--explain"])

    with pytest.raises(SystemExit, match="--json, --explain, --doctor and --bundle are mutually exclusive"):
        main([str(FIXTURES / "uefi_nvme_amd.json"), "--json", "--doctor"])

    with pytest.raises(SystemExit, match="--json, --explain, --doctor and --bundle are mutually exclusive"):
        main([str(FIXTURES / "uefi_nvme_amd.json"), "--doctor", "--bundle", "out"])


def test_cli_llm_provider_requires_explain() -> None:
    with pytest.raises(SystemExit, match="--llm-provider requires --explain"):
        main([
            str(FIXTURES / "uefi_nvme_amd.json"),
            "--llm-provider",
            "openai-compatible",
        ])


def test_cli_openai_compatible_provider_requires_api_key(monkeypatch) -> None:
    monkeypatch.delenv("AI_ADVISOR_OPENAI_API_KEY", raising=False)

    with pytest.raises(SystemExit, match="AI_ADVISOR_OPENAI_API_KEY"):
        main([
            str(FIXTURES / "uefi_nvme_amd.json"),
            "--explain",
            "--llm-provider",
            "openai-compatible",
        ])
