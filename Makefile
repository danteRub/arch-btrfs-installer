.PHONY: help setup test diagnose plan plan-json doctor explain explain-llm clean

PYTHON ?= python
REPORT ?= diagnostics/system_report.json
PLAN ?= plan.md
PLAN_JSON ?= plan.json
DOCTOR ?= doctor.md
EXPLANATION ?= explanation.md

help:
	@echo "Arch Btrfs AI Advisor commands"
	@echo ""
	@echo "Development:"
	@echo "  make setup        Create/update local editable install with dev dependencies"
	@echo "  make test         Run pytest"
	@echo "  make clean        Remove generated local outputs"
	@echo ""
	@echo "Diagnostics and planning:"
	@echo "  make diagnose     Generate diagnostics/system_report.json"
	@echo "  make plan         Generate Markdown plan to $(PLAN)"
	@echo "  make plan-json    Generate JSON plan to $(PLAN_JSON)"
	@echo "  make doctor       Generate doctor report to $(DOCTOR)"
	@echo "  make explain      Generate deterministic explanation to $(EXPLANATION)"
	@echo "  make explain-llm  Generate LLM explanation using openai-compatible provider"
	@echo ""
	@echo "Variables:"
	@echo "  REPORT=path/to/system_report.json"
	@echo "  PLAN=plan.md"
	@echo "  PLAN_JSON=plan.json"
	@echo "  DOCTOR=doctor.md"
	@echo "  EXPLANATION=explanation.md"

setup:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTHON) -m pytest -q

diagnose:
	./scripts/diagnostics.sh

plan:
	$(PYTHON) -m ai_advisor $(REPORT) --output $(PLAN)

plan-json:
	$(PYTHON) -m ai_advisor $(REPORT) --json --output $(PLAN_JSON)

doctor:
	$(PYTHON) -m ai_advisor $(REPORT) --doctor --output $(DOCTOR)

explain:
	$(PYTHON) -m ai_advisor $(REPORT) --explain --output $(EXPLANATION)

explain-llm:
	$(PYTHON) -m ai_advisor $(REPORT) --explain --llm-provider openai-compatible --output $(EXPLANATION)

clean:
	rm -f $(PLAN) $(PLAN_JSON) $(DOCTOR) $(EXPLANATION)
