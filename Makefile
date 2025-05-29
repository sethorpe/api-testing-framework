.PHONY: install lint test report serve-report clean all

# Install project dependencies without installing the root package
install:
	poetry install --no-root

# Run code style and lint checks
lint:
	black --check src tests
	isort --check-only src tests
	flake8 src tests

# Run unit tests
test:
	poetry run pytest

# Generate Allure results and HTML report
report:
	poetry run pytest --alluredir=allure-results
	allure generate allure-results --clean -o allure-report

# Serve the Allure report interactively
serve-report:
	python scripts/allure_helper.py --serve

# Clean test artifacts and reports
clean:
	rm -rf .pytest_cache/ allure-results/ allure-report/

# Full flow: clean state, install, lint, test, and report
all: clean install test report