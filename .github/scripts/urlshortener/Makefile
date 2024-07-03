install:
	@poetry install

lint: lint-pylint

lint-pylint:
	@poetry run pylint update_urls.py \
		--rcfile=./../../../pyproject.toml

test:
	@poetry run pytest ./test_update_urls.py \
		--cov update_urls \
		--cov-config ./../../../pyproject.toml
