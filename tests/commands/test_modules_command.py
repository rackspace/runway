"""Tests runway/commands/modules_command.py."""
# pylint: disable=no-self-use,redefined-outer-name
import os
from copy import deepcopy
from os import path

import pytest
import yaml
from mock import MagicMock, call, patch
from moto import mock_sts

from runway.commands.modules_command import (ModulesCommand,
                                             select_modules_to_run,
                                             validate_environment)
from runway.config import Config
from runway.util import environ

MODULE_PATH = 'runway.commands.modules_command'


@pytest.fixture(scope='function')
def module_tag_config():
    """Return a runway.yml file for testing module tags."""
    fixture_dir = path.join(
        path.dirname(path.dirname(path.realpath(__file__))),
        'fixtures'
    )
    with open(path.join(fixture_dir, 'tag.runway.yml'), 'r') as stream:
        return yaml.safe_load(stream)


class TestModulesCommand(object):
    """Test runway.commands.modules_command.ModulesCommand."""

    def test_run(self, monkeypatch):
        """Test run method."""
        # TODO test _process_deployments instead of mocking it out
        deployments = [{'modules': ['test'], 'regions':'us-east-1'}]
        test_config = Config(deployments=deployments, tests=[])
        get_env = MagicMock(return_value='test')

        monkeypatch.setattr(MODULE_PATH + '.select_modules_to_run',
                            lambda a, b, c, d, e: a)
        monkeypatch.setattr(MODULE_PATH + '.get_env', get_env)
        monkeypatch.setattr(Config, 'find_config_file',
                            MagicMock(return_value=os.getcwd() + 'runway.yml'))
        monkeypatch.setattr(ModulesCommand, 'runway_config', test_config)
        monkeypatch.setattr(ModulesCommand, '_process_deployments',
                            lambda obj, y, x: None)

        obj = ModulesCommand(cli_arguments={})

        with environ({}):
            os.environ.pop('CI', None)
            assert not obj.run(test_config.deployments, command='plan')
            os.environ['CI'] = '1'
            assert not obj.run(test_config.deployments, command='plan')

        get_env.assert_has_calls([call(os.getcwd(), False,
                                       prompt_if_unexpected=True),
                                  call(os.getcwd(), False,
                                       prompt_if_unexpected=False)])


class TestSelectModulesToRun(object):
    """Test runway.commands.modules_command.select_modules_to_run."""

    def test_tag_test_app(self, module_tag_config):
        """tag=[app:test-app] should return 2 modules."""
        tags = ['app:test-app']

        result = [
            select_modules_to_run(deployment, tags)
            for deployment in module_tag_config['deployments']
        ]
        assert len(result[0]['modules']) == 1
        assert result[0]['modules'][0]['path'] == 'sampleapp1.cfn'
        assert not result[1]['modules']
        assert len(result[2]['modules']) == 1
        assert result[2]['modules'][0]['path'] == 'sampleapp4.cfn'

    def test_tag_iac(self, module_tag_config):
        """tag=[tier:iac] should return 2 modules."""
        tags = ['tier:iac']

        result = [
            select_modules_to_run(deployment, tags)
            for deployment in module_tag_config['deployments']
        ]
        assert len(result[0]['modules']) == 2
        assert result[0]['modules'][0]['path'] == 'sampleapp1.cfn'
        assert result[0]['modules'][1]['path'] == 'sampleapp2.cfn'
        assert not result[1]['modules']
        assert not result[2]['modules']

    def test_two_tags(self, module_tag_config):
        """tag=[tier:iac, app:test-app] should return 1 module."""
        tags = ['tier:iac', 'app:test-app']
        result = [
            select_modules_to_run(deployment, tags)
            for deployment in module_tag_config['deployments']
        ]
        assert len(result[0]['modules']) == 1
        assert result[0]['modules'][0]['path'] == 'sampleapp1.cfn'
        assert not result[1]['modules']
        assert not result[2]['modules']

    def test_no_tags(self, module_tag_config):
        """tag=[] should request input."""
        user_input = ['1']
        with patch('runway.commands.modules_command.input',
                   side_effect=user_input):
            result = select_modules_to_run(
                module_tag_config['deployments'][0], []
            )
        assert result['modules'][0] == \
            module_tag_config['deployments'][0]['modules'][0]

    def test_no_tags_ci(self, module_tag_config):
        """tag=[], ci=true should not request input and return everything."""
        result = [
            select_modules_to_run(deployment, [], ci='true')
            for deployment in module_tag_config['deployments']
        ]
        assert result == module_tag_config['deployments']

    def test_destroy(self, module_tag_config):
        """command=destroy should only prompt with no tag of ci if one module."""
        user_input = ['y', '1']
        with patch('runway.commands.modules_command.input',
                   side_effect=user_input):
            result_single_no_tag = select_modules_to_run(
                deepcopy(module_tag_config['deployments'][1]), [], command='destroy'
            )
            result_no_tag = select_modules_to_run(
                deepcopy(module_tag_config['deployments'][0]), [], command='destroy'
            )
        assert result_single_no_tag['modules'][0] == \
            module_tag_config['deployments'][1]['modules'][0]
        assert result_no_tag['modules'][0] == \
            module_tag_config['deployments'][0]['modules'][0]
        result_tag = select_modules_to_run(
            deepcopy(module_tag_config['deployments'][0]), ['app:test-app'],
            command='destroy'
        )
        assert result_tag['modules'][0] == \
            module_tag_config['deployments'][0]['modules'][0]
        result_tag_ci = select_modules_to_run(
            deepcopy(module_tag_config['deployments'][0]), [], command='destroy',
            ci='true'
        )
        assert result_tag_ci['modules'] == \
            module_tag_config['deployments'][0]['modules']


class TestValidateEnvironment(object):
    """Tests for validate_environment."""

    MOCK_ACCOUNT_ID = '123456789012'

    def test_bool_match(self):
        """True bool should match."""
        assert validate_environment('test_module', True, os.environ)

    def test_bool_not_match(self):
        """False bool should not match."""
        assert not validate_environment('test_module', False, os.environ)

    @mock_sts
    def test_list_match(self):
        """Env in list should match."""
        assert validate_environment('test_module',
                                    [self.MOCK_ACCOUNT_ID + '/us-east-1'],
                                    os.environ)

    @mock_sts
    def test_list_not_match(self):
        """Env not in list should not match."""
        assert not validate_environment('test_module',
                                        [self.MOCK_ACCOUNT_ID + '/us-east-2'],
                                        os.environ)

    @mock_sts
    def test_str_match(self):
        """Env in string should match."""
        assert validate_environment('test_module',
                                    self.MOCK_ACCOUNT_ID + '/us-east-1',
                                    os.environ)

    @mock_sts
    def test_str_not_match(self):
        """Env not in string should not match."""
        assert not validate_environment('test_module',
                                        self.MOCK_ACCOUNT_ID + '/us-east-2',
                                        os.environ)
