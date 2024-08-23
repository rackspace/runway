#! /usr/bin/env bash

set -eo pipefail

function __install_poetry {
  if [[ -z "$(command -v poetry)" ]]; then
    pipx install poetry;
    pipx inject poetry "poetry-dynamic-versioning[plugin]" poetry-plugin-export;
  fi
}

function __configure_poetry {
  poetry config virtualenvs.create true;
  poetry config virtualenvs.in-project true;
  poetry config virtualenvs.prefer-active-python true;
  poetry config warnings.export false;
}

__install_poetry;
__configure_poetry;
