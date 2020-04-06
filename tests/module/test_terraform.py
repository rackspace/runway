"""Tests for terraform module."""
import unittest

from runway.module.terraform import update_env_vars_with_tf_var_values


class TerraformFunctionTester(unittest.TestCase):
    """Test Terraform module support functions."""

    def test_update_env_vars_with_tf_var_values(self):
        """Test update_env_vars_with_tf_var_values."""
        env_vars = update_env_vars_with_tf_var_values(
            {},
            {'foo': 'bar',
             'list': ['foo', 1, True],
             'map': {'one': 'two',
                     'three': 'four'}}
        )

        # This can be simplified post-python2 (with dict order preservation)
        # self.assertDictEqual(
        #     env_vars,
        #     {'TF_VAR_foo': 'bar',
        #     {'TF_VAR_list': '[test1,test2,test3]',
        #      'TF_VAR_map': '{ one = "two", three = "four" }'}
        # )
        self.assertTrue(env_vars['TF_VAR_foo'] == 'bar')
        self.assertTrue(env_vars['TF_VAR_list'] == '["foo", 1, true]')
        self.assertRegexpMatches(env_vars['TF_VAR_map'], r'one = "two"')  # noqa pylint: disable=deprecated-method
        self.assertRegexpMatches(env_vars['TF_VAR_map'], r'three = "four"')  # noqa pylint: disable=deprecated-method
