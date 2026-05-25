import json
from pathlib import Path

import pytest

from ai_advisor import SystemReport, create_initial_plan, summarize_hardware


FIXTURES = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> SystemReport:
    payload = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return SystemReport.model_validate(payload)


@pytest.mark.parametrize(
    ("fixture", "expected_summary", "expected_warning"),
    [
        ("uefi_without_efi.json", "UEFI", "no EFI partition"),
        ("multiple_disks.json", "UEFI", "Multiple disk candidates"),
        ("no_network.json", "UEFI", "No active network link"),
    ],
)
def test_fixture_scenarios_trigger_expected_warnings(
    fixture: str,
    expected_summary: str,
    expected_warning: str,
) -> None:
    report = _load_fixture(fixture)
    summary = summarize_hardware(report)
    plan = create_initial_plan(summary)

    warnings = "\n".join(plan.warnings)

    assert expected_summary in plan.summary
    assert expected_warning in warnings


def test_bios_fixture_uses_manual_bootloader_review() -> None:
    report = _load_fixture("bios_sata_intel.json")
    summary = summarize_hardware(report)
    plan = create_initial_plan(summary)

    assert "BIOS" in plan.summary
    assert "manual GRUB review" in plan.summary
    assert any("intel-ucode" in assumption for assumption in plan.assumptions)
    assert summary.disks[0].name == "sda"


def test_multiple_disks_fixture_detects_windows_and_multiple_disk_risks() -> None:
    report = _load_fixture("multiple_disks.json")
    summary = summarize_hardware(report)
    plan = create_initial_plan(summary)
    warnings = "\n".join(plan.warnings)

    assert len(summary.disks) == 2
    assert summary.possible_windows_dual_boot is True
    assert "Windows" in warnings
    assert "Multiple disk candidates" in warnings


def test_no_network_fixture_adds_network_verification_step() -> None:
    report = _load_fixture("no_network.json")
    summary = summarize_hardware(report)
    plan = create_initial_plan(summary)

    assert summary.network_link_up is False
    assert any(step.title == "Verify network before pacstrap" for step in plan.steps)
