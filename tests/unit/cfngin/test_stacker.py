"""Tests for runway.cfngin.stacker."""
import unittest

from runway.cfngin.commands import Stacker
from runway.cfngin.exceptions import InvalidConfig


class TestStacker(unittest.TestCase):
    """Tests for runway.cfngin.stacker.Stacker."""

    def test_stacker_build_parse_args(self):
        """Test stacker build parse args."""
        stacker = Stacker()
        args = stacker.parse_args(
            [
                "build",
                "-r",
                "us-west-2",
                "-e",
                "namespace=test.override",
                "tests/unit/cfngin/fixtures/basic.env",
                "tests/unit/cfngin/fixtures/vpc-bastion-db-web.yaml",
            ]
        )
        self.assertEqual(args.region, "us-west-2")
        self.assertFalse(args.outline)
        # verify namespace was modified
        self.assertEqual(args.environment["namespace"], "test.override")

    def test_stacker_build_parse_args_region_from_env(self):
        """Test stacker build parse args region from env."""
        stacker = Stacker()
        args = stacker.parse_args(
            [
                "build",
                "-e",
                "namespace=test.override",
                "tests/unit/cfngin/fixtures/basic.env",
                "tests/unit/cfngin/fixtures/vpc-bastion-db-web.yaml",
            ]
        )
        self.assertEqual(args.region, None)

    def test_stacker_build_context_passed_to_blueprint(self):
        """Test stacker build context passed to blueprint."""
        stacker = Stacker()
        args = stacker.parse_args(
            [
                "build",
                "-r",
                "us-west-2",
                "tests/unit/cfngin/fixtures/basic.env",
                "tests/unit/cfngin/fixtures/vpc-bastion-db-web.yaml",
            ]
        )
        stacker.configure(args)
        stacks_dict = args.context.get_stacks_dict()
        blueprint = stacks_dict[args.context.get_fqn("bastion")].blueprint
        self.assertTrue(hasattr(blueprint, "context"))
        blueprint.render_template()
        # verify that the bastion blueprint only contains blueprint variables,
        # not BaseDomain, AZCount or CidrBlock. Any variables that get passed
        # in from the command line shouldn't be resolved at the blueprint level
        self.assertNotIn("BaseDomain", blueprint.template.parameters)
        self.assertNotIn("AZCount", blueprint.template.parameters)
        self.assertNotIn("CidrBlock", blueprint.template.parameters)

    def test_stacker_blueprint_property_access_does_not_reset_blueprint(self):
        """Test stacker blueprint property access does not reset blueprint."""
        stacker = Stacker()
        args = stacker.parse_args(
            [
                "build",
                "-r",
                "us-west-2",
                "tests/unit/cfngin/fixtures/basic.env",
                "tests/unit/cfngin/fixtures/vpc-bastion-db-web.yaml",
            ]
        )
        stacker.configure(args)
        stacks_dict = args.context.get_stacks_dict()
        bastion_stack = stacks_dict[args.context.get_fqn("bastion")]
        bastion_stack.blueprint.render_template()
        self.assertIn("DefaultSG", bastion_stack.blueprint.template.parameters)

    def test_stacker_build_context_stack_names_specified(self):
        """Test stacker build context stack names specified."""
        stacker = Stacker()
        args = stacker.parse_args(
            [
                "build",
                "-r",
                "us-west-2",
                "tests/unit/cfngin/fixtures/basic.env",
                "tests/unit/cfngin/fixtures/vpc-bastion-db-web.yaml",
                "--stacks",
                "vpc",
                "--stacks",
                "bastion",
            ]
        )
        stacker.configure(args)
        stacks = args.context.get_stacks()
        self.assertEqual(len(stacks), 2)

    def test_stacker_build_fail_when_parameters_in_stack_def(self):
        """Test stacker build fail when parameters in stack def."""
        stacker = Stacker()
        args = stacker.parse_args(
            [
                "build",
                "-r",
                "us-west-2",
                "tests/unit/cfngin/fixtures/basic.env",
                "tests/unit/cfngin/fixtures/vpc-bastion-db-web-pre-1.0.yaml",
            ]
        )
        with self.assertRaises(InvalidConfig):
            stacker.configure(args)

    def test_stacker_build_custom_info_log_format(self):
        """Test stacker build custom info log format."""
        stacker = Stacker()
        args = stacker.parse_args(
            [
                "build",
                "-r",
                "us-west-2",
                "tests/unit/cfngin/fixtures/not-basic.env",
                "tests/unit/cfngin/fixtures/vpc-custom-log-format-info.yaml",
            ]
        )
        stacker.configure(args)
        self.assertEqual(
            stacker.config.log_formats["info"],
            "[%(asctime)s] test custom log format - %(message)s",
        )
        # for some reason, pylint does not see DictType.get as valid
        self.assertIsNone(
            stacker.config.log_formats.get("color")  # pylint: disable=no-member
        )
        self.assertIsNone(
            stacker.config.log_formats.get("debug")  # pylint: disable=no-member
        )


if __name__ == "__main__":
    unittest.main()
