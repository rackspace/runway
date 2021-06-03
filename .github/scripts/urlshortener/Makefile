install:
	@poetry install

lint: lint-flake8 lint-pylint

lint-flake8:
	@poetry run flake8 update_urls.py

lint-pylint:
	@poetry run pylint update_urls.py \
		--rcfile=./../../../pyproject.toml

test:
	@poetry run pytest ./test_update_urls.py \
		--cov update_urls \
		--cov-config ./../../../pyproject.toml
