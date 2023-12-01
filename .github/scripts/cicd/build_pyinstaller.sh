#!/usr/bin/env bash

# Create pyinstaller "onefile" build

set -ev

if [ "$OS_NAME" == "ubuntu-22.04" ]; then
    LOCAL_OS_NAME="linux"
elif [ "$OS_NAME" == "macos-12" ]; then
    LOCAL_OS_NAME="osx"
elif [ "$OS_NAME" == "windows-latest" ]; then
    LOCAL_OS_NAME="windows"
else
    echo 'Environment variable "OS_NAME" must be one of ["ubuntu-22.04", "macos-12", "windows-latest"]'
    exit 1
fi

if [ "$1" != "file" ] && [ "$1" != "folder" ]; then
    echo 'First positional argument must be one of ["file", "folder"]'
    exit 1
fi

RUNWAY_VERSION=$(poetry version --short)

poetry build
poetry run pip install "$(find dist -type f -name 'runway-*.tar.gz' -print | tail -n 1)"
find dist/* -exec rm -rfv "{}" +
mkdir -p "artifacts/${RUNWAY_VERSION}/${LOCAL_OS_NAME}"
poetry run pip show setuptools
poetry run pyinstaller --noconfirm --clean runway.$1.spec

if [ "$1" == 'file' ]; then
    mv dist/* "artifacts/${RUNWAY_VERSION}/$LOCAL_OS_NAME"
    chmod +x "artifacts/${RUNWAY_VERSION}/$LOCAL_OS_NAME/runway"
    # quick functional test
    ./artifacts/${RUNWAY_VERSION}/$LOCAL_OS_NAME/runway --version
else
    if [ "$OS_NAME" == "windows-latest" ]; then
        7z a -ttar -so ./runway.tar ./dist/runway/* | 7z a -si "./artifacts/${RUNWAY_VERSION}/${LOCAL_OS_NAME}/runway.tar.gz"
    else
        chmod +x dist/runway/runway-cli
        # quick functional test
        ./dist/runway/runway-cli --version
        tar -C dist/runway/ -czvf ."/artifacts/${RUNWAY_VERSION}/${LOCAL_OS_NAME}/runway.tar.gz" .
    fi
fi
