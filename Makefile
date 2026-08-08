# openDAW-MCP Pipeline Makefile
# Typical workflow: validate scripts → test → lint

VENV := venv/bin/python
EXPORTS := exports

.PHONY: help validate autofix clean test lint

help:
	@echo "openDAW-MCP Pipeline"
	@echo ""
	@echo "  make validate        Check all Werkstatt scripts"
	@echo "  make autofix         Auto-fix malformed @param declarations"
	@echo "  make test            Run pytest test suite"
	@echo "  make lint            Run ruff linter"
	@echo "  make clean           Remove exports"

validate:
	$(VENV) validate_scripts.py --all

autofix:
	$(VENV) autofix_params.py --all

test:
	python -m pytest tests/ -v

lint:
	ruff check server.py opendaw_mcp
	@echo "Ruff lint passed"
clean:
	rm -f $(EXPORTS)/*.wav

# Pre-commit hooks
.PHONY: precommit-install precommit-run precommit-update

precommit-install:
	pip install pre-commit
	pre-commit install

precommit-run:
	pre-commit run --all-files

precommit-update:
	pre-commit autoupdate
