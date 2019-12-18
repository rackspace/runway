IF "%1"=="test" (
    pipenv sync
    pipenv run python runner.py "%2"
)
