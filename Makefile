ifeq ($(TRAVIS_OS_NAME), osx)
	# the only os that defaults 'python' to python2
	PYTHON = python3
else
	PYTHON = python
endif


sync:
	PIPENV_VENV_IN_PROJECT=1 pipenv sync -d

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
	rm -rf runway.egg-info/
	rm -rf tmp/
	rm -rf src/
	rm -rf package.json postinstall.js preuninstall.js .coverage .npmignore

lint:
	pipenv run flake8 --exclude=runway/embedded,runway/templates runway
	find runway -name '*.py' -not -path 'runway/embedded*' -not -path 'runway/templates/stacker/*' -not -path 'runway/templates/cdk-py/*' -not -path 'runway/blueprints/*' | xargs pipenv run pylint --rcfile=.pylintrc
	find runway/blueprints -name '*.py' | xargs pipenv run pylint --disable=duplicate-code

test:
	pipenv run pytest

travistest: create_readme
	./.travis/test.sh

create_readme:
	sed '/^\[!\[Build Status\]/d' README.md | sed '/^\[!\[PyPi\]/d' | sed '/^\[!\[npm\]/d' | sed '/^\![\[runway\-example\.gif\]/d' | sed 's/^```yml$$/```/g' | sed 's/^```shell$$/```/g' |pandoc --from=markdown --to=rst --output=README.rst

create_tfenv_ver_file:
	curl --silent https://releases.hashicorp.com/index.json | jq -r '.terraform.versions | to_entries | map(select(.key | contains ("-") | not)) | sort_by(.key | split(".") | map(tonumber))[-1].key' | egrep -o '^[0-9]*\.[0-9]*\.[0-9]*' > runway/templates/terraform/.terraform-version

build: clean create_readme create_tfenv_ver_file
	python setup.py sdist

travisbuild_file: clean sync create_readme create_tfenv_ver_file
	pipenv run $(PYTHON) setup.py sdist
	mkdir -p tmp
	pipenv run pip install .
	pipenv run $(PYTHON) -c "from __future__ import print_function; import runway; print(runway.__version__, end='')" > tmp/version.txt
	mkdir -p artifacts/$$(cat tmp/version.txt)/pypi
	mkdir -p artifacts/$$(cat tmp/version.txt)/$(TRAVIS_OS_NAME)
	if [ $(TRAVIS_OS_NAME) = "linux" ]; then mv dist/* artifacts/$$(cat tmp/version.txt)/pypi; else rm -rf dist/runway-$$(cat tmp/version.txt).tar.gz; fi
	pipenv run pyinstaller --noconfirm --clean runway.file.spec
	mv dist/* artifacts/$$(cat tmp/version.txt)/$(TRAVIS_OS_NAME)

travisbuild_folder: clean sync create_readme create_tfenv_ver_file
	mkdir -p tmp
	pipenv run pip install .
	pipenv run $(PYTHON) -c "from __future__ import print_function; import runway; print(runway.__version__, end='')" > tmp/version.txt
	mkdir -p artifacts/$$(cat tmp/version.txt)/npm/$(TRAVIS_OS_NAME)
	pipenv run pyinstaller --noconfirm --clean runway.folder.spec
	if [ $(TRAVIS_OS_NAME) = "windows" ]; then \
		7z a -ttar -so ./runway.tar ./dist/runway/* | 7z a -si ./artifacts/$$(cat tmp/version.txt)/npm/$(TRAVIS_OS_NAME)/runway.tar.gz; \
	else \
		tar -C dist/runway/ -czvf ./artifacts/$$(cat tmp/version.txt)/npm/$(TRAVIS_OS_NAME)/runway.tar.gz .; \
	fi;

build_whl: clean create_readme create_tfenv_ver_file
	$(PYTHON) setup.py bdist_wheel --universal

release: clean create_readme create_tfenv_ver_file build
	twine upload dist/*
	curl -D - -X PURGE https://pypi.org/simple/runway

npm_prep: version_file
	cp npm/* . && cp npm/.[^.]* .
	jq ".version = \"$${NPM_PACKAGE_VERSION:-$$(cat tmp/version.txt)}\"" package.json > tmp/package.json
	jq ".name = \"$${NPM_PACKAGE_NAME-$${TRAVIS_BRANCH-undefined}}\"" tmp/package.json > package.json
	rm -rf tmp/package.json

version_file:
	mkdir -p tmp
	pipenv run $(PYTHON) -c "from __future__ import print_function; import runway; print(runway.__version__, end='')" > tmp/version.txt
