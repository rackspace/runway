"""Tests for module tags."""
from __future__ import print_function

import os
from copy import deepcopy

import boto3
import yaml
from send2trash import send2trash

from integration_tests.integration_test import IntegrationTest
from integration_tests.util import copy_dir, execute_tests, import_tests, run_command
from runway.util import change_dir

CFN_CLIENT = boto3.client("cloudformation", region_name="us-east-1")


class ModuleTags(IntegrationTest):
    """Base class for all module tag testing."""

    base_dir = os.path.abspath(os.path.dirname(__file__))
    tests_dir = os.path.join(base_dir, "tests")
    sampleapp_dir = os.path.join(base_dir, "sampleapp")

    cfngin_file = {
        "namespace": "runway-tests",
        "cfngin_bucket": "",
        "sys_path": "./",
        "stacks": {},
    }
    stack_definition = {"class_path": "blueprints.fake_stack.BlueprintClass"}

    def check_stacks(self, should_exist):
        """Check to see if stacks exist.

        Args:
            should_exist (str): List of sampleapp stack numbers that should
                be deployed.

        """
        stacks = {}

        for i in range(1, 7):
            stack_name = "runway-tests-module-tags-" + str(i)
            try:
                response = CFN_CLIENT.describe_stacks(StackName=stack_name)["Stacks"][0]
                if response["StackStatus"] == "CREATE_COMPLETE":
                    stacks[stack_name] = True
                else:
                    stacks[stack_name] = False
            except Exception:  # pylint: disable=broad-except
                stacks[stack_name] = False
        for stack, status in stacks.items():
            if stack[-1] in should_exist:
                assert status, stack + " exists in the account"
            else:
                assert not status, stack + " does not exist"
        return stacks

    def copy_sampleapp(self):
        """Create folder structure required for tests."""
        for i in range(1, 7):
            new_dir = os.path.join(self.base_dir, "sampleapp" + str(i))
            copy_dir(os.path.join(self.base_dir, "sampleapp"), new_dir)
            stacker_contents = deepcopy(self.cfngin_file)
            stacker_contents["stacks"] = {
                "module-tags-" + str(i): self.stack_definition
            }
            with open(os.path.join(new_dir, "stacker.yml"), "w+") as yml:
                yml.write(yaml.safe_dump(stacker_contents))

    def runway_cmd(self, command, tags):
        """Run a deploy command based on tags."""
        cmd = ["runway", command]
        for tag in tags:
            cmd.append("--tag")
            cmd.append(tag)
        self.logger.info("Running command: %s", str(cmd))
        with change_dir(self.base_dir):
            return run_command(cmd)

    def clean(self):
        """Delete test resources."""
        with change_dir(self.base_dir):
            for i in range(1, 7):
                dir_to_del = os.path.join(self.base_dir, "sampleapp" + str(i))
                if os.path.isdir(dir_to_del):
                    send2trash(dir_to_del)

    def run(self):
        """Find all tests and run them."""
        import_tests(self.logger, self.tests_dir, "test_*")
        self.set_environment("dev")
        self.set_env_var("CI", "1")
        tests = [test(self.logger) for test in ModuleTags.__subclasses__()]
        if not tests:
            raise Exception("No tests were found.")
        self.logger.debug("FOUND TESTS: %s", tests)
        err_count = execute_tests(tests, self.logger)
        assert err_count == 0  # assert that all subtests were successful
        return err_count

    def teardown(self):
        """Teardown resources create during init."""
        self.unset_env_var("CI")
        self.logger.debug(
            "Teardown is defined in the submodules, not "
            'the "ModuleTags" parent class.'
        )
