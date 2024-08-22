"""Tests for runway.cfngin.blueprints.testutil."""

import unittest

import pytest
from troposphere import ecr

from runway.cfngin.blueprints.base import Blueprint
from runway.cfngin.blueprints.testutil import BlueprintTestCase
from runway.context import CfnginContext
from runway.variables import Variable


class Repositories(Blueprint):
    """Simple blueprint to test our test cases."""

    VARIABLES = {
        "Repositories": {
            "type": list,
            "description": "A list of repository names to create.",
        }
    }

    def create_template(self) -> None:
        """Create template."""
        for repo in self.variables["Repositories"]:
            self.template.add_resource(ecr.Repository(f"{repo}Repository", RepositoryName=repo))


class TestRepositories(BlueprintTestCase):
    """Tests for runway.cfngin.blueprints.testutil.BlueprintTestCase."""

    OUTPUT_PATH = "tests/unit/fixtures/blueprints"

    def test_create_template_passes(self) -> None:
        """Test create template passes."""
        ctx = CfnginContext()
        blueprint = Repositories("test_repo", ctx)
        blueprint.resolve_variables([Variable("Repositories", ["repo1", "repo2"], "cfngin")])
        blueprint.create_template()
        self.assertRenderedBlueprint(blueprint)

    def test_create_template_fails(self) -> None:
        """Test create template fails."""
        ctx = CfnginContext()
        blueprint = Repositories("test_repo", ctx)
        blueprint.resolve_variables(
            [Variable("Repositories", ["repo1", "repo2", "repo3"], "cfngin")]
        )
        blueprint.create_template()
        with pytest.raises(AssertionError):
            self.assertRenderedBlueprint(blueprint)


if __name__ == "__main__":
    unittest.main()
