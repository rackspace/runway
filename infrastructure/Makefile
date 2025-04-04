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

plan:
	@pushd $(filter-out $@, $(MAKECMDGOALS))/common/ && \
		poetry run runway plan && \
		popd

%:
	@:
