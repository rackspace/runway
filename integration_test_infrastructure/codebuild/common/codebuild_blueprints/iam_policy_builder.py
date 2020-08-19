#!/usr/bin/env python
"""Module responsible of creating IAM roles."""
import logging
from os import path

import awacs.logs
import yaml
from awacs.aws import Allow, PolicyDocument, Statement
from troposphere import AccountId, Join, Partition, Region, iam

BASE_PATH = path.dirname(__file__)
LOGGER = logging.getLogger(__name__)


def create_base_policy():
    """Create the base policy."""
    deploy_name_list = ["runway-int-test-"]
    return iam.Policy(
        PolicyName="base-policy",
        PolicyDocument=PolicyDocument(
            Version="2012-10-17",
            Statement=[
                Statement(
                    Action=[
                        awacs.logs.CreateLogGroup,
                        awacs.logs.CreateLogStream,
                        awacs.logs.PutLogEvents,
                    ],
                    Effect=Allow,
                    Resource=[
                        Join(
                            "",
                            [
                                "arn:",
                                Partition,
                                ":logs:",
                                Region,
                                ":",
                                AccountId,
                                ":log-group:/aws/codebuild/",
                            ]
                            + deploy_name_list
                            + ["*"]
                            + x,
                        )
                        for x in [[":*"], [":*/*"]]
                    ],
                )
            ],
        ),
    )


class IAMPolicyFinder:
    """Class that finds the corresponding policies for the given integration test."""

    def __init__(self, root=None):
        """Set the root path of integration tests."""
        self.root = root or path.join(
            BASE_PATH, "..", "..", "..", "..", "integration_tests"
        )

    def file_path(self, test_name):
        """Get the policies file path for the given test."""
        folder = "test_{}".format(test_name.lower())
        return path.join(self.root, folder, "policies.yaml")

    def find(self, test_name):
        """Get the policies for the given integration test."""
        file_path = path.abspath(self.file_path(test_name))
        policies = []
        if path.isfile(file_path):
            with open(file_path, "r") as stream:
                entries = yaml.safe_load(stream)
                for entry in entries:
                    policy = iam.Policy(
                        PolicyName="inline-policy", PolicyDocument=entry
                    )
                    policies.append(policy)
        else:
            LOGGER.warning("policies.yaml not found for %s at %s", test_name, file_path)
        return policies


class IAMPolicyBuilder:
    """Utility class that builds IAM roles."""

    def __init__(self, policy_finder=None):
        """Set the policy finder."""
        self.policy_finder = policy_finder or IAMPolicyFinder("")

    def build(self, test_name):
        """Create policies for the given test."""
        policies = []
        policies.append(create_base_policy())
        for policy in self.policy_finder.find(test_name):
            policies.append(policy)
        return policies
