"""Tests for r4y.cfngin.blueprints.testutil."""
import unittest

from troposphere import ecr

from r4y.cfngin.blueprints.base import Blueprint
from r4y.cfngin.blueprints.testutil import BlueprintTestCase
from r4y.cfngin.context import Context
from r4y.variables import Variable


class Repositories(Blueprint):
    """Simple blueprint to test our test cases."""

    VARIABLES = {
        "Repositories": {
            "type": list,
            "description": "A list of repository names to create."
        }
    }

    def create_template(self):
        """Create template."""
        template = self.template
        variables = self.get_variables()

        for repo in variables["Repositories"]:
            template.add_resource(
                ecr.Repository(
                    "%sRepository" % repo,
                    RepositoryName=repo,
                )
            )


class TestRepositories(BlueprintTestCase):
    """Tests for r4y.cfngin.blueprints.testutil.BlueprintTestCase."""

    def test_create_template_passes(self):
        """Test create template passes."""
        ctx = Context({'namespace': 'test'})
        blueprint = Repositories('test_repo', ctx)
        blueprint.resolve_variables([
            Variable('Repositories', ["repo1", "repo2"], 'cfngin')
        ])
        blueprint.create_template()
        self.assertRenderedBlueprint(blueprint)

    def test_create_template_fails(self):
        """Test create template fails."""
        ctx = Context({'namespace': 'test'})
        blueprint = Repositories('test_repo', ctx)
        blueprint.resolve_variables([
            Variable('Repositories', ["repo1", "repo2", "repo3"], 'cfngin')
        ])
        blueprint.create_template()
        with self.assertRaises(AssertionError):
            self.assertRenderedBlueprint(blueprint)


if __name__ == '__main__':
    unittest.main()
