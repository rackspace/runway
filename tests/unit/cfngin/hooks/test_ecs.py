"""Tests for runway.cfngin.hooks.ecs."""
import unittest

import boto3
from moto import mock_ecs
from testfixtures import LogCapture

from runway.cfngin.hooks.ecs import create_clusters

from ..factories import mock_context, mock_provider

REGION = "us-east-1"


class TestECSHooks(unittest.TestCase):
    """Tests for runway.cfngin.hooks.ecs."""

    def setUp(self):
        """Run before tests."""
        self.provider = mock_provider(region=REGION)
        self.context = mock_context(namespace="fake")

    def test_create_single_cluster(self):
        """Test create single cluster."""
        with mock_ecs():
            cluster = "test-cluster"
            logger = "runway.cfngin.hooks.ecs"
            client = boto3.client("ecs", region_name=REGION)
            response = client.list_clusters()

            self.assertEqual(len(response["clusterArns"]), 0)
            with LogCapture(logger) as logs:
                self.assertTrue(
                    create_clusters(
                        provider=self.provider,
                        context=self.context,
                        clusters=cluster,
                    )
                )

                logs.check(
                    (
                        logger,
                        "DEBUG",
                        "Creating ECS cluster: %s" % cluster
                    )
                )

            response = client.list_clusters()
            self.assertEqual(len(response["clusterArns"]), 1)

    def test_create_multiple_clusters(self):
        """Test create multiple clusters."""
        with mock_ecs():
            clusters = ("test-cluster0", "test-cluster1")
            logger = "runway.cfngin.hooks.ecs"
            client = boto3.client("ecs", region_name=REGION)
            response = client.list_clusters()

            self.assertEqual(len(response["clusterArns"]), 0)
            for cluster in clusters:
                with LogCapture(logger) as logs:
                    self.assertTrue(
                        create_clusters(
                            provider=self.provider,
                            context=self.context,
                            clusters=cluster,
                        )
                    )

                    logs.check(
                        (
                            logger,
                            "DEBUG",
                            "Creating ECS cluster: %s" % cluster
                        )
                    )

            response = client.list_clusters()
            self.assertEqual(len(response["clusterArns"]), 2)

    def test_fail_create_cluster(self):
        """Test fail create cluster."""
        with mock_ecs():
            logger = "runway.cfngin.hooks.ecs"
            client = boto3.client("ecs", region_name=REGION)
            response = client.list_clusters()

            self.assertEqual(len(response["clusterArns"]), 0)
            with LogCapture(logger) as logs:
                create_clusters(
                    provider=self.provider,
                    context=self.context
                )

                logs.check(
                    (
                        logger,
                        "ERROR",
                        "setup_clusters hook missing \"clusters\" argument"
                    )
                )

            response = client.list_clusters()
            self.assertEqual(len(response["clusterArns"]), 0)
