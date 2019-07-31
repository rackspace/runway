plan:
	DEPLOY_ENVIRONMENT=dev pipenv run runway plan

deploy:
	DEPLOY_ENVIRONMENT=dev pipenv run runway deploy

test:
	pipenv sync
	DEPLOY_ENVIRONMENT=dev \
	CI=1 \
	pipenv run python terraform.py
