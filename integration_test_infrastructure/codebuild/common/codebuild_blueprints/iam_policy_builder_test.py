#!/usr/bin/env python
"""Test suite for the iam policy builder."""
import unittest
from unittest.mock import Mock, create_autospec

from iam_policy_builder import IAMPolicyBuilder, IAMPolicyFinder


class IAMPolicyFinderTest(unittest.TestCase):
    """Finder tests."""

    def test_file_path(self):
        """Tests the path is correct."""
        finder = IAMPolicyFinder("/")
        file_path = finder.file_path("my_test")
        self.assertEqual(file_path, "/test_my_test/policies.yaml")


class IAMPolicyBuilderTest(unittest.TestCase):
    """Builder tests."""

    def test_base_policy_present(self):
        """Tests the path is correct."""
        finder = create_autospec(IAMPolicyFinder, find=Mock(return_value=[]))
        builder = IAMPolicyBuilder(finder)
        policies = builder.build("my_test")
        self.assertEqual(len(policies), 1)
        self.assertEqual(policies[0].PolicyName, "base-policy")


if __name__ == "__main__":
    unittest.main()
