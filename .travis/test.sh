#!/usr/bin/env bash

set -ev

if [ "$TRAVIS_OS_NAME" = "osx" ]; then
    # the only os that defaults 'python' to python2
    PYTHON="python3"
else
    PYTHON="python"
fi

if [ "$TRAVIS_OS_NAME" = "osx" ] || [ "$TRAVIS_OS_NAME" = "windows" ]; then
    # these do not nativly run in a venv
    PIPENV="pipenv run "
fi

${PIPENV}${PYTHON} setup.py test

${PIPENV}flake8 --exclude=src/runway/cfngin,src/runway/embedded,src/runway/templates src/runway
find src/runway -name '*.py' -not -path 'src/runway/cfngin*' -not -path 'src/runway/embedded*' -not -path 'src/runway/templates/stacker/*' -not -path 'src/runway/templates/cdk-py/*' -not -path 'src/runway/blueprints/*' | xargs pipenv run ${PIPENV}pylint --rcfile=.pylintrc
find src/runway/blueprints -name '*.py' | xargs ${PIPENV}pylint --disable=duplicate-code
