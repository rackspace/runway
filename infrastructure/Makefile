sync:
	pipenv sync --dev

deploy:
	pushd $(filter-out $@, $(MAKECMDGOALS))/common/ && \
	PIPENV_MAX_DEPTH=5 pipenv run runway deploy && \
	popd

destroy:
	pushd $(filter-out $@, $(MAKECMDGOALS))/common/ && \
	PIPENV_MAX_DEPTH=5 pipenv run runway destroy && \
	popd

test:
	pushd $(filter-out $@, $(MAKECMDGOALS))/common/ && \
	PIPENV_MAX_DEPTH=5 pipenv run runway test && \
	popd

plan:
	pushd $(filter-out $@, $(MAKECMDGOALS))/common/ && \
	PIPENV_MAX_DEPTH=5 pipenv run runway plan && \
	popd

%:
	@:
