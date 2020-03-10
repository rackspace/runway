#!/usr/bin/env bash

# Create pyinstaller "onefile" build

set -ev

if [ "$OS_NAME" == "ubuntu-latest" ]; then
    LOCAL_OS_NAME="linux"
elif [ "$OS_NAME" == "macos-latest" ]; then
    LOCAL_OS_NAME="osx"
elif [ "$OS_NAME" == "windows-latest" ]; then
    LOCAL_OS_NAME="windows"
else
    echo 'Environment variable "OS_NAME" must be one of ["ubuntu-latest", "macos-latest", "windows-latest"]'
    exit 1
fi

if [ "$1" != "file" ] && [ "$1" != "folder" ]; then
    echo 'First positional argument must be one of ["file", "folder"]'
    exit 1
fi

RUNWAY_VERSION=`pipenv run python ./setup.py --version`

pipenv run python setup.py sdist
pipenv run pip install .
mkdir -p artifacts/$RUNWAY_VERSION/$LOCAL_OS_NAME
rm -rf dist/runway-$RUNWAY_VERSION.tar.gz
pipenv run pyinstaller --noconfirm --clean runway.$1.spec
mv dist/* artifacts/$RUNWAY_VERSION/$LOCAL_OS_NAME
