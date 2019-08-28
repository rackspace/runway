ifeq ($(TRAVIS_OS_NAME), osx)
	# the only os that defaults 'python' to python2
	PYTHON = python3
else
	PYTHON = python
endif


clean:
	rm -rf build/
	rm -rf dist/
	rm -rf runway.egg-info/
	rm -rf tmp/

test: create_readme
	pipenv sync -d
	pipenv run python setup.py test
	pipenv run flake8 --exclude=src/runway/embedded,src/runway/templates src/runway
	find src/runway -name '*.py' -not -path 'src/runway/embedded*' -not -path 'src/runway/templates/stacker/*' -not -path 'src/runway/templates/cdk-py/*' -not -path 'src/runway/blueprints/*' | xargs pipenv run pylint --rcfile=.pylintrc
	find src/runway/blueprints -name '*.py' | xargs pipenv run pylint --disable=duplicate-code

travistest: create_readme
	./.travis/test.sh

create_readme:
	sed '/^\[!\[Build Status\]/d' README.md | pandoc --from=markdown --to=rst --output=README.rst

create_tfenv_ver_file:
	curl --silent https://releases.hashicorp.com/index.json | jq -r '.terraform.versions | to_entries | map(select(.key | contains ("-") | not)) | sort_by(.key | split(".") | map(tonumber))[-1].key' | egrep -o '^[0-9]*\.[0-9]*\.[0-9]*' > src/runway/templates/terraform/.terraform-version

build: clean create_readme create_tfenv_ver_file
	python setup.py sdist

travisbuild: clean create_readme create_tfenv_ver_file
	pipenv sync --dev
	pipenv run $(PYTHON) setup.py sdist
	mkdir -p tmp
	pipenv run pip install .
	pipenv run $(PYTHON) -c "from __future__ import print_function; import runway; print(runway.__version__, end='')" > tmp/version.txt
	mkdir -p artifacts/$$(cat tmp/version.txt)/pypi
	mkdir -p artifacts/$$(cat tmp/version.txt)/$(TRAVIS_OS_NAME)
	if [ $(TRAVIS_OS_NAME) = "linux" ]; then mv dist/* artifacts/$$(cat tmp/version.txt)/pypi; else rm -rf dist/runway-$$(cat tmp/version.txt).tar.gz; fi
	pipenv run pyinstaller --noconfirm --clean runway.spec
	mv dist/* artifacts/$$(cat tmp/version.txt)/$(TRAVIS_OS_NAME)

build_whl: clean create_readme create_tfenv_ver_file
	$(PYTHON) setup.py bdist_wheel --universal

release: clean create_readme create_tfenv_ver_file build
	twine upload dist/*
	curl -D - -X PURGE https://pypi.org/simple/runway

npm_prep: version_file
	cp npm/* . && cp npm/.[^.]* .
	jq ".version = \"$$(cat tmp/version.txt)\"" package.json > tmp/package.json
	jq ".name = \"$${NPM_PACKAGE_NAME-$${TRAVIS_BRANCH-undefined}}\"" tmp/package.json > package.json
	# mv tmp/package.json package.json
	rm -rf tmp/package.json

version_file:
	mkdir -p tmp
	pipenv run $(PYTHON) -c "from __future__ import print_function; import runway; print(runway.__version__, end='')" > tmp/version.txt
