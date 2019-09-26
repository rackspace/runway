IF "%1"=="test" (
    set CI=1
    pipenv sync
    pipenv run python runner.py "%2"
)
