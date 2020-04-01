ifeq ($(TRAVIS_OS_NAME), osx)
	# the only os that defaults 'python' to python2
	PYTHON = python3
else
	PYTHON = python
endif


sync:
	PIPENV_VENV_IN_PROJECT=1 pipenv sync -d

# not actually a sync since we need to skip-lock but maintains naming
sync_two:
	PIPENV_VENV_IN_PROJECT=1 pipenv install --dev --two --skip-lock

# sync all virtual environments used by this project with their Pipfile.lock
sync_all:
	PIPENV_VENV_IN_PROJECT=1 pipenv sync --dev --three
	pushd docs && PIPENV_VENV_IN_PROJECT=1 pipenv sync --dev --three && popd
	pushd integration_tests && PIPENV_VENV_IN_PROJECT=1 pipenv sync --dev --three && popd
	pushd integration_test_infrastructure && PIPENV_VENV_IN_PROJECT=1 pipenv sync --dev --three && popd

# update all Pipfile.lock's used by this project
pipenv_lock:
	pipenv lock --dev
	pushd docs && pipenv lock --dev && popd
	pushd integration_tests && pipenv lock --dev && popd
	pushd integration_test_infrastructure && pipenv lock --dev && popd

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf r4y.egg-info/
	rm -rf tmp/
	rm -rf src/
	rm -rf package.json postinstall.js preuninstall.js .coverage .npmignore

lint:
	pipenv run flake8 --exclude=r4y/embedded,r4y/templates r4y
	find r4y -name '*.py' -not -path 'r4y/embedded*' -not -path 'r4y/templates/stacker/*' -not -path 'r4y/templates/cdk-py/*' -not -path 'r4y/blueprints/*' | xargs pipenv run pylint --rcfile=.pylintrc
	find r4y/blueprints -name '*.py' | xargs pipenv run pylint --disable=duplicate-code

test:
	pipenv run pytest

test_shim:
	./.travis/test_shim.sh

travistest:
	./.travis/test.sh


create_tfenv_ver_file:
	curl --silent https://releases.hashicorp.com/index.json | jq -r '.terraform.versions | to_entries | map(select(.key | contains ("-") | not)) | sort_by(.key | split(".") | map(tonumber))[-1].key' | egrep -o '^[0-9]*\.[0-9]*\.[0-9]*' > r4y/templates/terraform/.terraform-version

build: clean create_tfenv_ver_file
	python setup.py sdist

travisbuild_file: clean sync create_tfenv_ver_file
	pipenv run $(PYTHON) setup.py sdist
	mkdir -p tmp
	pipenv run pip install .
	pipenv run $(PYTHON) -c "from __future__ import print_function; import r4y; print(r4y.__version__, end='')" > tmp/version.txt
	mkdir -p artifacts/$$(cat tmp/version.txt)/pypi
	mkdir -p artifacts/$$(cat tmp/version.txt)/$(TRAVIS_OS_NAME)
	if [ $(TRAVIS_OS_NAME) = "linux" ]; then mv dist/* artifacts/$$(cat tmp/version.txt)/pypi; else rm -rf dist/r4y-$$(cat tmp/version.txt).tar.gz; fi
	pipenv run pyinstaller --noconfirm --clean r4y.file.spec
	mv dist/* artifacts/$$(cat tmp/version.txt)/$(TRAVIS_OS_NAME)

travisbuild_folder: clean sync create_tfenv_ver_file
	mkdir -p tmp
	pipenv run pip install .
	pipenv run $(PYTHON) -c "from __future__ import print_function; import r4y; print(r4y.__version__, end='')" > tmp/version.txt
	mkdir -p artifacts/$$(cat tmp/version.txt)/npm/$(TRAVIS_OS_NAME)
	pipenv run pyinstaller --noconfirm --clean r4y.folder.spec
	if [ $(TRAVIS_OS_NAME) = "windows" ]; then \
		7z a -ttar -so ./r4y.tar ./dist/r4y/* | 7z a -si ./artifacts/$$(cat tmp/version.txt)/npm/$(TRAVIS_OS_NAME)/r4y.tar.gz; \
	else \
		tar -C dist/r4y/ -czvf ./artifacts/$$(cat tmp/version.txt)/npm/$(TRAVIS_OS_NAME)/r4y.tar.gz .; \
	fi;

build_whl: clean create_tfenv_ver_file
	$(PYTHON) setup.py bdist_wheel --universal

release: clean create_tfenv_ver_file build
	twine upload dist/*
	curl -D - -X PURGE https://pypi.org/simple/r4y

npm_prep: version_file
	cp npm/* . && cp npm/.[^.]* .
	jq ".version = \"$${NPM_PACKAGE_VERSION:-$$(cat tmp/version.txt)}\"" package.json > tmp/package.json
	jq ".name = \"$${NPM_PACKAGE_NAME-$${TRAVIS_BRANCH-undefined}}\"" tmp/package.json > package.json
	rm -rf tmp/package.json

version_file:
	mkdir -p tmp
	pipenv run $(PYTHON) -c "from __future__ import print_function; import r4y; print(r4y.__version__, end='')" > tmp/version.txt
