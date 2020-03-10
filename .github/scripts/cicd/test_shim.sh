#!/usr/bin/env bash

# A simple script for testing the stacker => runway.cfngin shim

set -ev

cfngin_config() {
    cat <<'HERE'
namespace: runway-shim-test
cfngin_bucket: ''

sys_path: ./integration_tests/test_moduletags/sampleapp

stacks:
  shim_test:
    class_path: blueprints.fake_stack.BlueprintClass
    variables:
      TestVar: '${default something::something_else}'
HERE
}

pipenv run runway run-stacker -- build <(cfngin_config) --dump .github/temp
rm -rf .github/temp/stack_templates
