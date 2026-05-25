import json
from pathlib import Path

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
