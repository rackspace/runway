.PHONY: build clean docs help install lint list release test

SHELL := /bin/bash

ifeq ($(CI), yes)
	POETRY_OPTS = "-v"
	PRE_COMMIT_OPTS = --show-diff-on-failure --verbose
endif

help: ## show this message
	@awk \
		'BEGIN {FS = ":.*##"; printf "\nUsage: make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-30s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) }' \
		$(MAKEFILE_LIST)


build: clean create-tfenv-ver-file ## build the PyPi release
	@poetry build

build-pyinstaller-file: clean create-tfenv-ver-file ## build Pyinstaller single file release (github)
	@poetry dynamic-versioning
	bash ./.github/scripts/cicd/build_pyinstaller.sh file

build-pyinstaller-folder: clean create-tfenv-ver-file ## build Pyinstaller folder release (github)
	@poetry dynamic-versioning
	bash ./.github/scripts/cicd/build_pyinstaller.sh folder

clean: ## remove generated file from the project directory
	rm -rf ./build/ ./dist/ ./src/ ./tmp/ ./runway.egg-info/;
	rm -rf ./.pytest_cache ./.venv;
	find . -type d -name ".venv" -prune -exec rm -rf '{}' +;
	find . -type d -name "node_modules" -prune -exec rm -rf '{}' +;
	find . -type d -name ".runway" -prune -exec rm -rf '{}' +;
	find . -type f -name "*.py[co]" -delete;
	find . -type d -name "__pycache__" -prune -exec rm -rf '{}' +;
	@$(MAKE) --no-print-directory -C docs clean;

cov-report: ## display a report in the terminal of files missing coverage
	@poetry run coverage report \
		--precision=2 \
		--show-missing \
		--skip-covered \
		--skip-empty \
		--rcfile=pyproject.toml

cov-xml: ## convert .coverage to coverage.xml for use with codecov
	@poetry run coverage xml \
		--ignore-errors \
		--rcfile=pyproject.toml
	@echo ""
	@echo ".coverage converted to coverage.xml"
	@echo ""

create-tfenv-ver-file: ## create a tfenv version file using the latest version
	curl --silent https://releases.hashicorp.com/index.json | jq -r '.terraform.versions | to_entries | map(select(.key | contains ("-") | not)) | sort_by(.key | split(".") | map(tonumber))[-1].key' | egrep -o '^[0-9]*\.[0-9]*\.[0-9]*' > runway/templates/terraform/.terraform-version

docs: ## delete current HTML docs & build fresh HTML docs
	@$(MAKE) --no-print-directory -C docs docs

docs-changes: ## build HTML docs; only builds changes detected by Sphinx
	@$(MAKE) --no-print-directory -C docs html

fix: fix-ruff fix-black run-pre-commit ## run all automatic fixes

fix-black: ## automatically fix all black errors
	@poetry run black .

fix-imports: ## automatically fix all import sorting errors
	@poetry run ruff check . --fix-only --fixable I001

fix-ruff: ## automatically fix everything ruff can fix (implies fix-imports)
	@poetry run ruff check . --fix-only

fix-ruff-tests:
	@poetry run ruff check ./tests --fix-only --unsafe-fixes

lint: lint-black lint-ruff lint-pyright ## run all linters

lint-black: ## run black
	@echo "Running black... If this fails, run 'make fix-black' to resolve."
	@poetry run black . --check --color --diff
	@echo ""

lint-pyright: ## run pyright
	@echo "Running pyright..."
	@npm exec --no -- pyright --venv-path ./
	@echo ""

lint-ruff: ## run ruff
	@echo "Running ruff... If this fails, run 'make fix-ruff' to resolve some error automatically, other require manual action."
	@poetry run ruff check .
	@echo ""

npm-ci: ## run "npm ci" with the option to ignore scripts - required to succeed for this project
	@npm ci --ignore-scripts

npm-install: ## run "npm install" with the option to ignore scripts - required to succeed for this project
	@npm install --ignore-scripts

# copies artifacts to src & npm package files to the root of the repo
npm-prep: ## process that needs to be run before creating an npm package
	mkdir -p tmp
	mkdir -p src
	npm version $$(poetry version --short) --allow-same-version --no-git-tag-version
	cp -r artifacts/$$(poetry version --short)/* src/
	cp npm/* . && cp npm/.[^.]* .
	cp package.json tmp/package.json
	jq ".name = \"$${NPM_PACKAGE_NAME-undefined}\"" tmp/package.json > package.json
	rm -rf tmp/package.json

open-docs: ## open docs (HTML files must already exists)
	@make -C docs open

run-pre-commit: ## run pre-commit for all files
	@poetry run pre-commit run $(PRE_COMMIT_OPTS) \
		--all-files \
		--color always

setup: setup-poetry setup-pre-commit setup-npm ## setup development environment

setup-npm: npm-ci ## install node dependencies with npm

setup-poetry: ## setup python virtual environment
	@poetry install $(POETRY_OPTS) --sync

setup-pre-commit: ## install pre-commit git hooks
	@poetry run pre-commit install

spellcheck: ## run cspell
	@echo "Running cSpell to checking spelling..."
	@npm exec --no -- cspell lint . \
		--color \
		--config .vscode/cspell.json \
		--dot \
		--gitignore \
		--must-find-files \
		--no-progress \
		--relative \
		--show-context

test: ## run integration and unit tests
	@echo "Running integration & unit tests..."
	@poetry run pytest \
		--cov runway \
		--cov-report term-missing:skip-covered \
		--dist loadfile \
		--integration \
		--numprocesses auto

test-functional: ## run function tests only
	@echo "Running functional tests..."
	@if [ $${CI} ]; then \
		echo "  using pytest-xdist"; \
		poetry run pytest \
			--dist loadfile \
			--functional \
			--log-cli-format "[%(levelname)s] %(message)s" \
			--log-cli-level 15 \
			--no-cov \
			--numprocesses auto; \
	else \
		echo "  not using pytest-xdist"; \
		poetry run pytest \
			--functional \
			--log-cli-format "[%(levelname)s] %(message)s" \
			--log-cli-level 15 \
			--no-cov; \
	fi

test-integration: ## run integration tests only
	@echo "Running integration tests..."
	@poetry run pytest \
		--cov runway \
		--cov-report term-missing:skip-covered \
		--dist loadfile \
		--integration-only \
		--numprocesses auto

test-unit: ## run unit tests only
	@echo "Running unit tests..."
	@poetry run pytest \
		--cov=runway \
		--cov-config=tests/unit/.coveragerc \
		--cov-report term-missing:skip-covered
