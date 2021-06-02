.PHONY: blueprints public test test-alt

SHELL := /bin/bash

install:
	@poetry install

deploy:
	@pushd $(filter-out $@, $(MAKECMDGOALS))/common/ && \
		poetry run runway deploy && \
		popd

destroy:
	@pushd $(filter-out $@, $(MAKECMDGOALS))/common/ && \
		poetry run runway destroy && \
		popd

test:
	@pushd $(filter-out $@, $(MAKECMDGOALS))/common/ && \
		poetry run runway test && \
		popd

plan:
	@pushd $(filter-out $@, $(MAKECMDGOALS))/common/ && \
		poetry run runway plan && \
		popd

%:
	@:
