# openDAW-MCP Pipeline Makefile
# Typical workflow: validate scripts → premix → master → compare

VENV := venv/bin/python
CHROME := PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/google-chrome
EXPORTS := exports

.PHONY: help validate premix master compare clean test lint

help:
	@echo "openDAW-MCP Pipeline"
	@echo ""
	@echo "  make validate        Check all Werkstatt scripts"
	@echo "  make autofix         Auto-fix malformed @param declarations"
	@echo "  make premix          Render premix from produce_stems.py"
	@echo "  make master          Post-master (pro5 default)"
	@echo "  make master-pro3     Post-master (pro3, commercial loud)"
	@echo "  make compare         A/B compare last 3 exports"
	@echo "  make pipeline        Full: validate → premix → master → compare"
	@echo "  make test-ssl        Test ssl_bus_comp"
	@echo "  make test            Run pytest test suite"
	@echo "  make lint            Run ruff linter"
	@echo "  make clean           Remove exports"

validate:
	$(VENV) validate_scripts.py --all

autofix:
	$(VENV) autofix_params.py --all

premix:
	$(CHROME) $(VENV) produce_stems.py

master:
	$(VENV) post_master_pro5.py

master-pro3:
	$(VENV) post_master_pro3.py

compare:
	$(VENV) compare_versions.py --last $(EXPORTS)/ 3

pipeline: validate premix master compare

test-ssl:
	$(CHROME) $(VENV) test_ssl_bus_comp.py

test:
	python -m pytest tests/ -v

lint:
	ruff check server.py
	@echo "Ruff lint passed"

clean:
	rm -f $(EXPORTS)/*.wav
