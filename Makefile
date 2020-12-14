.PHONY: help list sync sync_two sync_all pipenv_lock clean fix-isort lint lint-flake8 lint-isort lint-pylint lint_two test test-integration test-unit test_shim create_tfenv_ver_file build build_pyinstaller_file build_pyinstaller_folder build_whl release npm_prep

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

list: ## list all targets in this Makefile
	@$(MAKE) -pRrq -f $(lastword $(MAKEFILE_LIST)) : 2>/dev/null | awk -v RS= -F: '/^# File/,/^# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' | sort | egrep -v -e '^[^[:alnum:]]' -e '^$@$$'

sync: ## create a python virtual environment in the project for development
	PIPENV_VENV_IN_PROJECT=1 pipenv sync --dev
	pipenv run pre-commit install

# changes that need to be made inorder to sync python two (may also require deletion of the existing lock file)
sync_two:  ## create a python virtual environment in the project for python 2 development
	PIPENV_VENV_IN_PROJECT=1 pipenv install "astroid<2.0" "pylint<2.0" "pydocstyle<4.0.0" "isort[pyproject]>=4.2.5" --dev --skip-lock --two

sync_all: sync ## sync all virtual environments used by this project with their Pipfile.lock
	pushd docs && PIPENV_VENV_IN_PROJECT=1 pipenv sync --dev --three && popd
	pushd integration_tests && PIPENV_VENV_IN_PROJECT=1 pipenv sync --dev --three && popd
	pushd integration_test_infrastructure && PIPENV_VENV_IN_PROJECT=1 pipenv sync --dev --three && popd

pipenv_lock: ## update all Pipfile.lock's used by this project
	pipenv lock --dev
	pushd docs && pipenv lock --dev && popd
	pushd integration_tests && pipenv lock --dev && popd
	pushd integration_test_infrastructure && pipenv lock --dev && popd

pipenv-update:
	pipenv update --dev --keep-outdated
	pushd docs && pipenv update --dev --keep-outdated && popd
	pushd integration_tests && pipenv update --dev --keep-outdated && popd
	pushd integration_test_infrastructure && pipenv update --dev --keep-outdated && popd

clean: ## remove generated file from the project directory
	rm -rf build/
	rm -rf dist/
	rm -rf runway.egg-info/
	rm -rf tmp/
	rm -rf src/
	rm -rf package.json postinstall.js preuninstall.js .coverage .npmignore

fix-black: ## automatically fix all black errors
	@pipenv run black .

fix-isort: ## automatically fix all isort errors
	@pipenv run isort . --recursive --atomic

lint: lint-isort lint-black lint-flake8 lint-pylint ## run all linters

lint-black: ## run black
	@echo "Running black... If this fails, run 'make fix-black' to resolve."
	@pipenv run black . --check
	@echo ""

lint-flake8: ## run flake8
	@echo "Running flake8..."
	@pipenv run flake8 --docstring-convention=all
	@echo ""

lint-isort: ## run isort
	@echo "Running isort... If this fails, run 'make fix-isort' to resolve."
	@pipenv run isort . --check-only
	@echo ""

lint-pylint: ## run pylint
	@echo "Running pylint..."
	@find runway -name '*.py' -not -path 'runway/embedded*' -not -path 'runway/templates/stacker/*' -not -path 'runway/templates/cdk-py/*' -not -path 'runway/blueprints/*' | xargs pipenv run pylint --rcfile=.pylintrc
	@echo ""

# linting for python 2, requires additional disables
lint_two: ## run all linters (python 2 only)
	pipenv run flake8 --config=setup.cfg --exclude=runway/embedded,runway/hooks/staticsite/auth_at_edge/templates,runway/templates --extend-ignore=D101,D202,D403,E124,E203,W504 runway
	find runway -name '*.py' -not -path 'runway/embedded*' -not -path 'runway/hooks/staticsite/auth_at_edge/templates*' -not -path 'runway/templates/stacker/*' -not -path 'runway/templates/cdk-py/*' -not -path 'runway/blueprints/*' | xargs pipenv run pylint --rcfile=.pylintrc --disable=bad-continuation,bad-option-value,bad-whitespace,method-hidden,no-member,no-name-in-module,relative-import,unused-import,wrong-import-order

test: ## run integration and unit tests
	@echo "Running integration & unit tests..."
	@pipenv run pytest --cov=runway --cov-report term:skip-covered --integration

test-functional: ## run function tests only
	@echo "Running functional tests..."
	@pipenv run pytest --functional --no-cov

test-integration: ## run integration tests only
	@echo "Running integration tests..."
	@pipenv run pytest --cov=runway --cov-report term:skip-covered --integration-only

test-unit: ## run unit tests only
	@echo "Running unit tests..."
	@pipenv run pytest --cov=runway --cov-config=tests/unit/.coveragerc --cov-report term-missing

test_shim: ## run a test for the stacker shim
	bash ./.github/scripts/cicd/test_shim.sh

create_tfenv_ver_file: ## create a tfenv version file using the latest version
	curl --silent https://releases.hashicorp.com/index.json | jq -r '.terraform.versions | to_entries | map(select(.key | contains ("-") | not)) | sort_by(.key | split(".") | map(tonumber))[-1].key' | egrep -o '^[0-9]*\.[0-9]*\.[0-9]*' > runway/templates/terraform/.terraform-version

build: clean create_tfenv_ver_file ## build the PyPi release
	python setup.py sdist

build_pyinstaller_file: clean create_tfenv_ver_file ## build Pyinstaller single file release (github)
	bash ./.github/scripts/cicd/build_pyinstaller.sh file

build_pyinstaller_folder: clean create_tfenv_ver_file ## build Pyinstaller folder release(github)
	bash ./.github/scripts/cicd/build_pyinstaller.sh folder

build_whl: clean create_tfenv_ver_file ## build wheel
	python setup.py bdist_wheel --universal

release: clean create_tfenv_ver_file build # publish to PyPi
	twine upload dist/*
	curl -D - -X PURGE https://pypi.org/simple/runway

# requires setuptools-scm and setuptools global python installs
# copies artifacts to src & npm package files to the root of the repo
# updates package.json with the name of the package & semver version from scm (formated for npm)
npm_prep: ## process that needs to be run before creating an npm package
	mkdir -p tmp
	mkdir -p src
	cp -r artifacts/$$(python ./setup.py --version)/* src/
	cp npm/* . && cp npm/.[^.]* .
	jq ".version = \"$${NPM_PACKAGE_VERSION:-$$(python ./setup.py --version | sed -E "s/\.dev/-dev/")}\"" package.json > tmp/package.json
	jq ".name = \"$${NPM_PACKAGE_NAME-undefined}\"" tmp/package.json > package.json
	rm -rf tmp/package.json
