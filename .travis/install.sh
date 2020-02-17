#!/usr/bin/env bash

set -ev

if [ "$TRAVIS_OS_NAME" = "osx" ]; then
    # the only os that defaults 'python' to python2
    PYTHON="python3"
else
    PYTHON="python"
fi

${PYTHON} -m ensurepip

if [ "$TRAVIS_OS_NAME" = "osx" ] || [ "$TRAVIS_OS_NAME" = "windows" ]; then
    # these setup steps are already taken care of for linux in travis's
    # images. but, since windows and osx don't 'support' the python language
    # option, we have to do this here.
    ${PYTHON} --version && pip --version
    ${PYTHON} -m pip install --upgrade pip setuptools
fi

# virtualenv 20 was a complete rewrite and includes some breaking changes
# with how we were handling things like distutils. These version are now pinned
# to ensure compatability.
pip install "virtualenv==20.0.1" "pipenv==2018.11.26"

# anything running python3 can use the provided Pipfile.lock
if [ "$PYTHON_VERSION" != "2.7" ]; then
    pipenv sync --three --dev
else
    # if we use the provided Pipfile.lock with python2, it will always try
    # to install pylint>=2.0 which is not supported. so, remove the lock
    # and define an appropriate version to install.
    rm -rf Pipfile.lock
    pipenv install "pylint<2.0" --dev
    pipenv sync --dev
fi
