PYTHON ?= python
export PYTHONDONTWRITEBYTECODE := 1

.PHONY: gate
gate:
	$(PYTHON) -m ruff check --no-cache .
	$(PYTHON) -m ruff format --check --no-cache .
	$(PYTHON) -m pytest -q -p no:cacheprovider
	@tmpdist="$$(mktemp -d)"; \
	trap 'rm -rf "$$tmpdist" build src/*.egg-info' EXIT; \
	$(PYTHON) -m build --sdist --wheel --outdir "$$tmpdist"; \
	$(PYTHON) -m twine check "$$tmpdist"/*
