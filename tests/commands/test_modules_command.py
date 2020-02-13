"""Tests runway/commands/modules_command.py."""
import os
import unittest
from copy import deepcopy
from os import path

import yaml
from mock import patch
from moto import mock_sts

from runway.commands.modules_command import (select_modules_to_run,
                                             validate_environment)


def module_tag_config():
    """Return a runway.yml file for testing module tags."""
    fixture_dir = path.join(
        path.dirname(path.dirname(path.realpath(__file__))),
        'fixtures'
    )
    with open(path.join(fixture_dir, 'tag.runway.yml'), 'r') as stream:
        return yaml.safe_load(stream)


class ModulesCommandTestCase(unittest.TestCase):
    """Test runway/commands/modules_command.py."""

    tag_yml = module_tag_config()

    def test_select_modules_to_run_tag_test_app(self):
        """tag=[app:test-app] should return 2 modules."""
        config = deepcopy(ModulesCommandTestCase.tag_yml)
        tags = ['app:test-app']

        result = [
            select_modules_to_run(deployment, tags)
            for deployment in config['deployments']
        ]
        self.assertEqual(len(result[0]['modules']), 1)
        self.assertEqual(result[0]['modules'][0]['path'], 'sampleapp1.cfn')
        self.assertEqual(len(result[1]['modules']), 0)
        self.assertEqual(len(result[2]['modules']), 1)
        self.assertEqual(result[2]['modules'][0]['path'], 'sampleapp4.cfn')

    def test_select_modules_to_run_tag_iac(self):
        """tag=[tier:iac] should return 2 modules."""
        config = deepcopy(ModulesCommandTestCase.tag_yml)
        tags = ['tier:iac']

        result = [
            select_modules_to_run(deployment, tags)
            for deployment in config['deployments']
        ]
        self.assertEqual(len(result[0]['modules']), 2)
        self.assertEqual(result[0]['modules'][0]['path'], 'sampleapp1.cfn')
        self.assertEqual(result[0]['modules'][1]['path'], 'sampleapp2.cfn')
        self.assertEqual(len(result[1]['modules']), 0)
        self.assertEqual(len(result[2]['modules']), 0)

    def test_select_modules_to_run_two_tags(self):
        """tag=[tier:iac, app:test-app] should return 1 module."""
        config = deepcopy(ModulesCommandTestCase.tag_yml)
        tags = ['tier:iac', 'app:test-app']
        result = [
            select_modules_to_run(deployment, tags)
            for deployment in config['deployments']
        ]
        self.assertEqual(len(result[0]['modules']), 1)
        self.assertEqual(result[0]['modules'][0]['path'], 'sampleapp1.cfn')
        self.assertEqual(len(result[1]['modules']), 0)
        self.assertEqual(len(result[2]['modules']), 0)

    def test_select_modules_to_run_no_tags(self):
        """tag=[] should request input."""
        config = deepcopy(ModulesCommandTestCase.tag_yml)
        user_input = ['1']
        with patch('runway.commands.modules_command.input',
                   side_effect=user_input):
            result = select_modules_to_run(
                config['deployments'][0], []
            )
        self.assertEqual(result['modules'][0],
                         config['deployments'][0]['modules'][0])

    def test_select_modules_to_run_no_tags_ci(self):
        """tag=[], ci=true should not request input and return everything."""
        config = deepcopy(ModulesCommandTestCase.tag_yml)
        result = [
            select_modules_to_run(deployment, [], ci='true')
            for deployment in config['deployments']
        ]
        self.assertEqual(result, config['deployments'])

    def test_select_modules_to_run_destroy(self):
        """command=destroy should only prompt with no tag of ci if one module."""
        config = deepcopy(ModulesCommandTestCase.tag_yml)
        user_input = ['y', '1']
        with patch('runway.commands.modules_command.input',
                   side_effect=user_input):
            result_single_no_tag = select_modules_to_run(
                deepcopy(config['deployments'][1]), [], command='destroy'
            )
            result_no_tag = select_modules_to_run(
                deepcopy(config['deployments'][0]), [], command='destroy'
            )
        self.assertEqual(result_single_no_tag['modules'][0],
                         config['deployments'][1]['modules'][0])
        self.assertEqual(result_no_tag['modules'][0],
                         config['deployments'][0]['modules'][0])
        result_tag = select_modules_to_run(
            deepcopy(config['deployments'][0]), ['app:test-app'],
            command='destroy'
        )
        self.assertEqual(result_tag['modules'][0],
                         config['deployments'][0]['modules'][0])
        result_tag_ci = select_modules_to_run(
            deepcopy(config['deployments'][0]), [], command='destroy',
            ci='true'
        )
        self.assertEqual(result_tag_ci['modules'],
                         config['deployments'][0]['modules'])


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
