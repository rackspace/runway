#! /usr/bin/env bash

set -eo pipefail

function __install_poetry {
  if [[ -z "$(command -v poetry)" ]]; then
    pipx install poetry;
    pipx inject poetry "poetry-dynamic-versioning[plugin]" poetry-plugin-export;
  fi
}

function __configure_poetry {
  # defaults to `~/.cache/pypoetry`, using a volume for anything inside of `~/.cache` causes dotfile to not be installed
  poetry config cache-dir "${HOME}/.cache-pypoetry"
  poetry config virtualenvs.create true;
  poetry config virtualenvs.in-project true;
}

__install_poetry;
__configure_poetry;
