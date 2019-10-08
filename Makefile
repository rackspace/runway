clean:
	rm -rf build/
	rm -rf dist/
	rm -rf runway.egg-info/

test: create_readme
	pipenv sync -d
	pipenv run python setup.py test
	pipenv run flake8 --exclude=src/runway/embedded,src/runway/templates src/runway
	find src/runway -name '*.py' -not -path 'src/runway/embedded*' -not -path 'src/runway/templates/stacker/*' -not -path 'src/runway/templates/cdk-py/*' -not -path 'src/runway/blueprints/*' | xargs pipenv run pylint --rcfile=.pylintrc
	find src/runway/blueprints -name '*.py' | xargs pipenv run pylint --disable=duplicate-code

travistest: create_readme
	python setup.py test
	flake8 --exclude=src/runway/embedded,src/runway/templates src/runway
	find src/runway -name '*.py' -not -path 'src/runway/embedded*' -not -path 'src/runway/templates/stacker/*' -not -path 'src/runway/templates/cdk-py/*' -not -path 'src/runway/blueprints/*' | PYTHONPATH=src xargs pylint --rcfile=.pylintrc
	find src/runway/blueprints -name '*.py' | xargs pylint --disable=duplicate-code

create_readme:
	sed '/^\[!\[Build Status\]/d' README.md | pandoc --from=markdown --to=rst --output=README.rst

create_tfenv_ver_file:
	curl --silent https://releases.hashicorp.com/index.json | jq -r '.terraform.versions | to_entries | map(select(.key | contains ("-") | not)) | sort_by(.key | split(".") | map(tonumber))[-1].key' | egrep -o '^[0-9]*\.[0-9]*\.[0-9]*' > src/runway/templates/terraform/.terraform-version

build: clean create_readme create_tfenv_ver_file
	python setup.py sdist

build_whl: clean create_readme create_tfenv_ver_file
	python setup.py bdist_wheel --universal

release: clean create_readme create_tfenv_ver_file build
	twine upload dist/*
	curl -D - -X PURGE https://pypi.org/simple/runway

travis: travistest clean create_tfenv_ver_file build
