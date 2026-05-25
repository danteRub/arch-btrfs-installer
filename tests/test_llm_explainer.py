from ai_advisor import (
    build_llm_explanation_prompt,
    create_initial_plan,
    explain_plan,
    explain_plan_with_optional_llm,
    validate_llm_explanation,
)
from ai_advisor.hardware_parser import DiskCandidate, HardwareSummary


class FakeSafeClient:
    def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        assert "must not" in system_prompt.lower()
        assert "InstallPlan JSON" in user_prompt
        return """# LLM explanation

This is advisory only.

The command `./01-installer.sh` is critical and requires human confirmation.

Windows or NTFS markers were detected; avoid wiping disks without review.
Do not wipe any disk until the target disk and EFI partition have been manually verified.
"""


class FakeUnsafeClient:
    def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        return "Looks safe. Just continue."


def _plan_with_windows_warning():
    summary = HardwareSummary(
        boot_mode="UEFI",
        cpu_vendor="GenuineIntel",
        microcode_package="intel-ucode",
        network_link_up=True,
        disks=[DiskCandidate(name="sda", has_windows_markers=True)],
        possible_windows_dual_boot=True,
        warnings=["Windows or NTFS markers were detected; avoid wiping disks without review."],
    )
    return create_initial_plan(summary)


def test_build_llm_prompt_contains_plan_and_safety_rules() -> None:
    plan = _plan_with_windows_warning()
    prompt = build_llm_explanation_prompt(plan)

    assert "InstallPlan JSON" in prompt
    assert "Do not change risk labels" in prompt
    assert "./01-installer.sh" in prompt
    assert "Windows or NTFS" in prompt


def test_optional_llm_without_client_uses_deterministic_fallback() -> None:
    plan = _plan_with_windows_warning()
    result = explain_plan_with_optional_llm(plan)

    assert result.used_llm is False
    assert result.explanation == explain_plan(plan)
    assert result.deterministic_fallback == explain_plan(plan)


def test_optional_llm_uses_safe_client_response() -> None:
    plan = _plan_with_windows_warning()
    result = explain_plan_with_optional_llm(plan, client=FakeSafeClient())

    assert result.used_llm is True
    assert "LLM explanation" in result.explanation
    assert "./01-installer.sh" in result.explanation
    assert "human confirmation" in result.explanation


def test_optional_llm_rejects_unsafe_response_and_falls_back() -> None:
    plan = _plan_with_windows_warning()
    result = explain_plan_with_optional_llm(plan, client=FakeUnsafeClient())

    assert result.used_llm is False
    assert result.explanation == explain_plan(plan)


def test_validate_llm_explanation_reports_missing_safety_signals() -> None:
    plan = _plan_with_windows_warning()
    errors = validate_llm_explanation(plan, "Looks safe. Just continue.")

    assert any("Missing warning signal" in error for error in errors)
    assert any("Missing critical command" in error for error in errors)
