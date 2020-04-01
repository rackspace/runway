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

${PIPENV}pytest

${PIPENV}flake8 --exclude=r4y/cfngin,r4y/embedded,r4y/templates r4y
find r4y -name '*.py' -not -path 'r4y/cfngin*' -not -path 'r4y/embedded*' -not -path 'r4y/templates/stacker/*' -not -path 'r4y/templates/cdk-py/*' -not -path 'r4y/blueprints/*' | xargs pipenv run ${PIPENV}pylint --rcfile=.pylintrc
find r4y/blueprints -name '*.py' | xargs ${PIPENV}pylint --disable=duplicate-code
bash .travis/test_shim.sh
