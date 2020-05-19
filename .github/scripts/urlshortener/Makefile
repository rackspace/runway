export:
	pipenv lock --requirements > requirements.txt

lint: lint-flake8 lint-pylint lint-mypy

lint-flake8:
	pipenv run flake8 update_urls.py --max-line-length 98

lint-mypy:
	pipenv run mypy update_urls.py --ignore-missing-imports

lint-pylint:
	pipenv run pylint update_urls.py --rcfile=./../../../.pylintrc

sync:
	pipenv sync --dev

test:
	pipenv run pytest ./test_update_urls.py --cov=update_urls
