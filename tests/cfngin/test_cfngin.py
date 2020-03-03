"""Tests for runway.cfngin entry point."""
# pylint: disable=no-self-use,protected-access
import os
import shutil

from mock import MagicMock, patch

from runway.cfngin import CFNgin
from runway.context import Context
from runway.util import AWS_ENV_VARS


def copy_fixture(src, dest):
    """Wrap shutil.copy to backport use with Path objects."""
    return shutil.copy(str(src.absolute()), str(dest.absolute()))


def copy_basic_fixtures(cfngin_fixtures, tmp_path):
    """Copy the basic env file and config file to a tmp_path."""
    copy_fixture(src=cfngin_fixtures / 'envs' / 'basic.env',
                 dest=tmp_path / 'test-us-east-1.env')
    copy_fixture(src=cfngin_fixtures / 'configs' / 'basic.yml',
                 dest=tmp_path / 'basic.yml')


def get_env_creds():
    """Return AWS creds from the environment."""
    return {name: os.environ.get(name) for name in AWS_ENV_VARS if os.environ.get(name)}


class TestCFNgin(object):
    """Test runway.cfngin.CFNgin."""

    @staticmethod
    def configure_mock_action_instance(mock_action):
        """Configure a mock action."""
        mock_instance = MagicMock(return_value=None)
        mock_action.return_value = mock_instance
        mock_instance.execute = MagicMock()
        return mock_instance

    @staticmethod
    def get_context(name='test', region='us-east-1'):
        """Create a basic Runway context object."""
        return Context(env_name=name,
                       env_region=region,
                       env_root=os.getcwd())

    def test_env_file(self, tmp_path):
        """Test that the correct env file is selected."""
        test_env = tmp_path / 'test.env'
        test_env.write_text('test_value: test')

        result = CFNgin(ctx=self.get_context(), sys_path=str(tmp_path))
        assert result.env_file.test_value == 'test'

        test_us_east_1 = tmp_path / 'test-us-east-1.env'
        test_us_east_1.write_text('test_value: test-us-east-1')

        test_us_west_2 = tmp_path / 'test-us-west-2.env'
        test_us_west_2.write_text('test_value: test-us-west-2')

        lab_ca_central_1 = tmp_path / 'lab-ca-central-1.env'
        lab_ca_central_1.write_text('test_value: lab-ca-central-1')

        result = CFNgin(ctx=self.get_context(), sys_path=str(tmp_path))
        assert result.env_file.test_value == 'test-us-east-1'

        result = CFNgin(ctx=self.get_context(region='us-west-2'),
                        sys_path=str(tmp_path))
        assert result.env_file.test_value == 'test-us-west-2'

        result = CFNgin(ctx=self.get_context(name='lab',
                                             region='ca-central-1'),
                        sys_path=str(tmp_path))
        assert result.env_file.test_value == 'lab-ca-central-1'

    @patch('runway.cfngin.actions.build.Action')
    def test_deploy(self, mock_action, cfngin_fixtures, tmp_path):
        """Test deploy with two files & class init."""
        mock_instance = self.configure_mock_action_instance(mock_action)
        copy_basic_fixtures(cfngin_fixtures, tmp_path)
        copy_fixture(src=cfngin_fixtures / 'configs' / 'basic.yml',
                     dest=tmp_path / 'basic2.yml')

        context = self.get_context()
        context.env_vars['CI'] = '1'

        cfngin = CFNgin(ctx=context,
                        parameters={'test_param': 'test-param-value'},
                        sys_path=str(tmp_path))
        cfngin.deploy()

        assert get_env_creds() == cfngin._aws_credential_backup, \
            'env vars should be reverted upon completion'
        assert cfngin.concurrency == 0
        assert not cfngin.interactive
        assert cfngin.parameters.bucket_name == 'cfngin-bucket'
        assert cfngin.parameters.environment == 'test'
        assert cfngin.parameters.namespace == 'test-namespace'
        assert cfngin.parameters.region == 'us-east-1'
        assert cfngin.parameters.test_key == 'test_value'
        assert cfngin.parameters.test_param == 'test-param-value'
        assert cfngin.recreate_failed
        assert cfngin.region == 'us-east-1'
        assert cfngin.sys_path == tmp_path
        assert not cfngin.tail

        assert mock_action.call_count == 2
        mock_instance.execute.has_calls([{'concurrency': 0,
                                          'tail': False},
                                         {'concurrency': 0,
                                          'tail': False}])

    @patch('runway.cfngin.actions.destroy.Action')
    def test_destroy(self, mock_action, cfngin_fixtures, tmp_path):
        """Test destroy."""
        mock_instance = self.configure_mock_action_instance(mock_action)
        copy_basic_fixtures(cfngin_fixtures, tmp_path)

        cfngin = CFNgin(ctx=self.get_context(), sys_path=str(tmp_path))
        cfngin.destroy()

        assert get_env_creds() == cfngin._aws_credential_backup, \
            'env vars should be reverted upon completion'
        mock_action.assert_called_once()
        mock_instance.execute.assert_called_once_with(concurrency=0,
                                                      force=True,
                                                      tail=False)

    def test_load(self, cfngin_fixtures, tmp_path):
        """Test load."""
        copy_basic_fixtures(cfngin_fixtures, tmp_path)
        cfngin = CFNgin(ctx=self.get_context(), sys_path=str(tmp_path))
        result = cfngin.load(tmp_path / 'basic.yml')

        assert not result.bucket_name
        assert result.namespace == 'test-namespace'
        assert len(result.get_stacks()) == 1
        assert result.get_stacks()[0].name == 'test-stack'

    @patch('runway.cfngin.actions.diff.Action')
    def test_plan(self, mock_action, cfngin_fixtures, tmp_path):
        """Test plan."""
        mock_instance = self.configure_mock_action_instance(mock_action)
        copy_basic_fixtures(cfngin_fixtures, tmp_path)

        cfngin = CFNgin(ctx=self.get_context(), sys_path=str(tmp_path))
        cfngin.plan()

        assert get_env_creds() == cfngin._aws_credential_backup, \
            'env vars should be reverted upon completion'
        mock_action.assert_called_once()
        mock_instance.execute.assert_called_once_with()

    def test_find_config_files(self, tmp_path):
        """Test find_config_files."""
        bad_path = tmp_path / 'bad_path'
        bad_path.mkdir()
        # tmp_path.stem

        good_config_paths = [
            tmp_path / '_t3sT.yaml',
            tmp_path / '_t3sT.yml',
            tmp_path / '01-config.yaml',
            tmp_path / '01-config.yml',
            tmp_path / 'TeSt_02.yaml',
            tmp_path / 'TeSt_02.yml',
            tmp_path / 'test.config.yaml',
            tmp_path / 'test.config.yml'
        ]
        bad_config_paths = [
            tmp_path / '.anything.yaml',
            tmp_path / '.gitlab-ci.yml',
            tmp_path / 'docker-compose.yml',
            bad_path / '00-invalid.yml'
        ]

        for config_path in good_config_paths + bad_config_paths:
            config_path.write_text('')

        result = CFNgin.find_config_files(sys_path=str(tmp_path))
        expected = sorted([str(config_path)
                           for config_path in good_config_paths])
        assert result == expected

        result = CFNgin.find_config_files(
            sys_path=str(tmp_path / '01-config.yml')
        )
        assert result == [tmp_path / '01-config.yml']

        result = CFNgin.find_config_files()
        assert not result
