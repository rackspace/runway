clean:
	rm -rf build/
	rm -rf dist/
	rm -rf runway.egg-info/

test:
	flake8 --exclude=runway/embedded runway
	find runway -name '*.py' -not -path 'runway/embedded*' -not -path 'runway/templates/stacker/*' | xargs pylint
	find runway/templates/stacker -name '*.py' | xargs pylint --disable=import-error --disable=too-few-public-methods

create_readme:
	pandoc --from=markdown --to=rst --output=README.rst README.md

build: clean create_readme
	python setup.py sdist

build_whl: clean create_readme
	python setup.py bdist_wheel --universal

release: clean create_readme build
	twine upload dist/*

travis: test clean create_readme build
