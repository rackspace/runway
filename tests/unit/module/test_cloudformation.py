"""Test runway.module.cloudformation."""
# pylint: disable=protected-access,no-self-use
import os

from mock import patch

from runway.context import Context
from runway.module.cloudformation import CloudFormation
from runway.util import MutableMap


class TestCloudFormation(object):
    """Test runway.module.cloudformation.CloudFormation."""

    @property
    def generic_options(self):
        """Return generic module options."""
        return {
            'environment': True,
            'parameters': MutableMap(**{
                'test_key': 'test-value'
            })
        }

    @staticmethod
    def get_context(name='test', region='us-east-1'):
        """Create a basic Runway context object."""
        return Context(env_name=name,
                       env_region=region,
                       env_root=os.getcwd())

    @patch('runway.cfngin.CFNgin.deploy')
    def test_deploy(self, mock_action, tmp_path):
        """Test deploy."""
        module = CloudFormation(self.get_context(),
                                str(tmp_path),
                                self.generic_options)
        module.deploy()
        mock_action.assert_called_once()

    @patch('runway.cfngin.CFNgin.destroy')
    def test_destroy(self, mock_action, tmp_path):
        """Test destroy."""
        module = CloudFormation(self.get_context(),
                                str(tmp_path),
                                self.generic_options)
        module.destroy()
        mock_action.assert_called_once()

    @patch('runway.cfngin.CFNgin.plan')
    def test_plan(self, mock_action, tmp_path):
        """Test plan."""
        module = CloudFormation(self.get_context(),
                                str(tmp_path),
                                self.generic_options)
        module.plan()
        mock_action.assert_called_once()
