#!/usr/bin/env bash

# A simple script for testing the stacker => r4y.cfngin shim

if [ "$TRAVIS_OS_NAME" = "osx" ] || [ "$TRAVIS_OS_NAME" = "windows" ] || [ -z "$TRAVIS_OS_NAME"]; then
    # these do not nativly run in a venv
    PIPENV="pipenv run "
fi

set -ev

cfngin_config() {
    cat <<'HERE'
namespace: r4y-shim-test
cfngin_bucket: ''

sys_path: ./integration_tests/test_moduletags/sampleapp

stacks:
  shim_test:
    class_path: blueprints.fake_stack.BlueprintClass
    variables:
      TestVar: '${default something::something_else}'
HERE
}

# AWS_SECRET_ACCESS_KEY required to pass in forked travis runs
AWS_SECRET_ACCESS_KEY=1 ${PIPENV}r4y run-stacker -- build <(cfngin_config) --dump .travis
rm -rf .travis/stack_templates
