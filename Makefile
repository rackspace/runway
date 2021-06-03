.PHONY: help list install install-all clean fix-isort lint lint-flake8 lint-isort lint-pylint lint_two test test-integration test-unit create-tfenv-ver-file build build-pyinstaller-file build-pyinstaller-folder build-whl release npm-prep

SHELL := /bin/bash

help: ## show this message
	@IFS=$$'\n' ; \
	help_lines=(`fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##/:/'`); \
	printf "%-30s %s\n" "target" "help" ; \
	printf "%-30s %s\n" "------" "----" ; \
	for help_line in $${help_lines[@]}; do \
		IFS=$$':' ; \
		help_split=($$help_line) ; \
		help_command=`echo $${help_split[0]} | sed -e 's/^ *//' -e 's/ *$$//'` ; \
		help_info=`echo $${help_split[2]} | sed -e 's/^ *//' -e 's/ *$$//'` ; \
		printf '\033[36m'; \
		printf "%-30s %s" $$help_command ; \
		printf '\033[0m'; \
		printf "%s\n" $$help_info; \
	done

build: clean create-tfenv-ver-file ## build the PyPi release
	python setup.py sdist

build-pyinstaller-file: clean create-tfenv-ver-file ## build Pyinstaller single file release (github)
	bash ./.github/scripts/cicd/build_pyinstaller.sh file

build-pyinstaller-folder: clean create-tfenv-ver-file ## build Pyinstaller folder release(github)
	bash ./.github/scripts/cicd/build_pyinstaller.sh folder

build-whl: clean create-tfenv-ver-file ## build wheel
	python setup.py bdist_wheel --universal

clean: ## remove generated file from the project directory
	rm -rf build/
	rm -rf dist/
	rm -rf runway.egg-info/
	rm -rf tmp/
	rm -rf src/
	rm -rf postinstall.js preuninstall.js .coverage .npmignore
	find . -name ".runway" -type d -prune -exec rm -rf '{}' +

cov-report: ## display a report in the terminal of files missing coverage
	@poetry run coverage report \
		--precision=2 \
		--show-missing \
		--skip-covered \
		--skip-empty \
		--rcfile=pyproject.toml

create-tfenv-ver-file: ## create a tfenv version file using the latest version
	curl --silent https://releases.hashicorp.com/index.json | jq -r '.terraform.versions | to_entries | map(select(.key | contains ("-") | not)) | sort_by(.key | split(".") | map(tonumber))[-1].key' | egrep -o '^[0-9]*\.[0-9]*\.[0-9]*' > runway/templates/terraform/.terraform-version

fix-black: ## automatically fix all black errors
	@poetry run black .

fix-isort: ## automatically fix all isort errors
	@poetry run isort .

install: ## create a python virtual environment in the project for development
	@poetry install --remove-untracked

install-docs: ## create a python virtual environment for building documentation
	@pushd docs && \
		poetry install --remove-untracked && \
		popd

install-all: install install-docs ## setup all virtual environments used by this project

lint: lint-isort lint-black lint-pyright lint-flake8 lint-pylint ## run all linters

lint-black: ## run black
	@echo "Running black... If this fails, run 'make fix-black' to resolve."
	@poetry run black . --check --color --diff
	@echo ""

lint-cspell: ## run cspell
	@echo "Running cSpell to checking spelling..."
	@npx cspell "**/*" --color --config .vscode/cspell.json --must-find-files
	@echo ""

lint-flake8: ## run flake8
	@echo "Running flake8..."
	@poetry run flake8 --config=setup.cfg
	@echo ""

lint-isort: ## run isort
	@echo "Running isort... If this fails, run 'make fix-isort' to resolve."
	@poetry run isort . --check-only
	@echo ""

lint-pylint: ## run pylint
	@echo "Running pylint..."
	@poetry run pylint runway tests --rcfile=pyproject.toml
	@echo ""

lint-pyright: ## run pyright
	@echo "Running pyright..."
	@npm run-script py-type-check
	@echo ""

npm-ci: ## run "npm ci" with the option to ignore scripts - required to succeed for this project
	@npm ci --ignore-scripts

npm-install: ## run "npm install" with the option to ignore scripts - required to succeed for this project
	@npm install --ignore-scripts

# requires setuptools-scm and setuptools global python installs
# copies artifacts to src & npm package files to the root of the repo
# updates package.json with the name of the package & semver version from scm (formatted for npm)
npm-prep: ## process that needs to be run before creating an npm package
	mkdir -p tmp
	mkdir -p src
	cp -r artifacts/$$(python ./setup.py --version)/* src/
	cp npm/* . && cp npm/.[^.]* .
	jq ".version = \"$${NPM_PACKAGE_VERSION:-$$(python ./setup.py --version | sed -E "s/\.dev/-dev/")}\"" package.json > tmp/package.json
	jq ".name = \"$${NPM_PACKAGE_NAME-undefined}\"" tmp/package.json > package.json
	rm -rf tmp/package.json

release: clean create-tfenv-ver-file build # publish to PyPi
	twine upload dist/*
	curl -D - -X PURGE https://pypi.org/simple/runway

run-pre-commit: ## run pre-commit for all files
	@poetry run pre-commit run -a

setup: npm-ci install install-docs setup-pre-commit ## setup development environment

setup-pre-commit: ## install pre-commit git hooks
	@poetry run pre-commit install

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
	@poetry run pytest
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

update: ## update project python environment
	@poetry update

update-docs: ## update python virtual environment for building documentation
	@pushd docs && \
		poetry update && \
		popd

update-all: update update-docs ## update all python environments
