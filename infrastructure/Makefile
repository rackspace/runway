sync:
	pipenv sync --dev

deploy: sync
	pushd $(filter-out $@, $(MAKECMDGOALS))/common/ && \
	PIPENV_MAX_DEPTH=5 pipenv run runway deploy && \
	popd

destroy: sync
	pushd $(filter-out $@, $(MAKECMDGOALS))/common/ && \
	PIPENV_MAX_DEPTH=5 pipenv run runway destroy && \
	popd

test: sync
	pushd $(filter-out $@, $(MAKECMDGOALS))/common/ && \
	PIPENV_MAX_DEPTH=5 pipenv run runway test && \
	popd

plan: sync
	pushd $(filter-out $@, $(MAKECMDGOALS))/common/ && \
	PIPENV_MAX_DEPTH=5 pipenv run runway plan && \
	popd

%:
	@:
