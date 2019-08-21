test:
	pipenv sync
	DEPLOY_ENVIRONMENT=dev \
	CI=1 \
	pipenv run python runner.py
