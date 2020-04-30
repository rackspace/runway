"""Tests for terraform module."""
# pylint: disable=no-self-use,unused-argument
import sys
from contextlib import contextmanager
from datetime import datetime

import boto3
import pytest
from botocore.stub import Stubber
from mock import patch

from runway.module.terraform import (TerraformBackendConfig, TerraformOptions,
                                     update_env_vars_with_tf_var_values)


@contextmanager
def does_not_raise():
    """Use for conditional pytest.raises when using parametrize."""
    yield


def test_update_env_vars_with_tf_var_values():
    """Test update_env_vars_with_tf_var_values."""
    result = update_env_vars_with_tf_var_values({}, {'foo': 'bar',
                                                     'list': ['foo', 1, True],
                                                     'map': sorted({  # python 2
                                                         'one': 'two',
                                                         'three': 'four'
                                                     })})
    expected = {
        'TF_VAR_foo': 'bar',
        'TF_VAR_list': '["foo", 1, true]',
        'TF_VAR_map': '{ one = "two", three = "four" }'
    }

    assert sorted(result) == sorted(expected)  # sorted() needed for python 2


class TestTerraformOptions(object):
    """Test runway.module.terraform.TerraformOptions."""

    @pytest.mark.parametrize('config', [
        ({'args': ['-key=val']}),
        ({'args': {'apply': ['-key=apply']}}),
        ({'args': {'init': ['-key=init']}}),
        ({'args': {'plan': ['-key=plan']}}),
        ({'args': {'apply': ['-key=apply'], 'init': ['-key=init']}}),
        ({'args': {'apply': ['-key=apply'],
                   'init': ['-key=init'],
                   'plan': ['-key=plan']}}),
        ({'terraform_backend_config': {'bucket': 'foo',
                                       'dynamodb_table': 'bar',
                                       'region': 'us-west-2'}}),
        ({'terraform_backend_config': {'region': 'us-west-2'},
          'terraform_backend_cfn_outputs': {'bucket': 'foo',
                                            'dynamodb_table': 'bar'}}),
        ({'terraform_backend_config': {'region': 'us-west-2'},
          'terraform_backend_ssm_params': {'bucket': 'foo',
                                           'dynamodb_table': 'bar'}}),
        ({'terraform_version': '0.11.6'}),
        ({'terraform_version': {'test': '0.12', 'prod': '0.11.6'}}),  # deprecated
        ({'args': {'apply': ['-key=apply'],
                   'init': ['-key=init'],
                   'plan': ['-key=plan']},
          'terraform_backend_config': {'region': 'us-west-2'},
          'terraform_backend_ssm_params': {'bucket': 'foo',
                                           'dynamodb_table': 'bar'},
          'terraform_version': {'test': '0.12', 'prod': '0.11.6'}}),  # deprecated
        ({'args': {'apply': ['-key=apply'],
                   'init': ['-key=init'],
                   'plan': ['-key=plan']},
          'terraform_backend_config': {'bucket': 'foo',
                                       'dynamodb_table': 'bar',
                                       'region': 'us-west-2'},
          'terraform_version': '0.11.6'}),
        ({'args': ['-key=val'],  # deprecated
          'terraform_backend_config': {'test': {'bucket': 'foo',
                                                'dynamodb_table': 'bar'},
                                       'prod': {'bucket': 'invalid',
                                                'dynamodb_table': 'invalid'}},
          'terraform_version': {'test': '0.12', 'prod': '0.11.6'}})
    ])
    @patch('runway.module.terraform.TerraformBackendConfig.parse')
    def test_parse(self, mock_backend, config, monkeypatch, runway_context):
        """Test parse."""
        mock_backend.return_value = 'successfully parsed backend'

        if sys.version_info.major < 3:  # python 2 support
            @staticmethod
            def assert_resolve_version_kwargs(context, terraform_version=None,
                                              **_):
                """Assert args passed to the method during parse."""
                assert config.get('terraform_version') == terraform_version
                return 'successfully resolved version'
        else:
            def assert_resolve_version_kwargs(context, terraform_version=None,
                                              **_):
                """Assert args passed to the method during parse."""
                assert config.get('terraform_version') == terraform_version
                return 'successfully resolved version'

        monkeypatch.setattr(TerraformOptions, 'resolve_version',
                            assert_resolve_version_kwargs)

        result = TerraformOptions.parse(context=runway_context,
                                        path='./', **config)

        if isinstance(config.get('args'), list):
            assert result.args['apply'] == config['args']
            assert result.args['init'] == []
            assert result.args['plan'] == []
        elif isinstance(config.get('args'), dict):
            assert result.args['apply'] == config['args'].get('apply', [])
            assert result.args['init'] == config['args'].get('init', [])
            assert result.args['plan'] == config['args'].get('plan', [])
        assert result.backend_config == 'successfully parsed backend'
        assert result.version == 'successfully resolved version'
        mock_backend.assert_called_once_with(runway_context, './', **config)

    @pytest.mark.parametrize('terraform_version, expected, exception',
                             [('0.11.6', '0.11.6', does_not_raise()),
                              ({'test': '0.12', 'prod': '0.11.6'},  # deprecated
                               '0.12', does_not_raise()),
                              ({'*': '0.11.6', 'test': '0.12'},  # deprecated
                               '0.12', does_not_raise()),
                              ({'*': '0.11.6', 'prod': '0.12'},  # deprecated
                               '0.11.6', does_not_raise()),
                              ({'prod': '0.11.6'}, None,  # deprecated
                               does_not_raise()),
                              (None, None, does_not_raise()),
                              (13, None, pytest.raises(TypeError))])
    def test_resolve_version(self, runway_context, terraform_version,
                             expected, exception):
        """Test resolve_version."""
        config = {'something': None}
        if terraform_version:
            config['terraform_version'] = terraform_version
        with exception:
            assert TerraformOptions.resolve_version(runway_context,
                                                    **config) == expected


class TestTerraformBackendConfig(object):
    """Test runway.module.terraform.TerraformBackendConfig."""

    @pytest.mark.parametrize('input_data, expected_items', [
        ({}, []),
        ({'bucket': 'test-bucket'}, ['bucket=test-bucket']),
        ({'dynamodb_table': 'test-table'}, ['dynamodb_table=test-table']),
        ({'region': 'us-east-1'}, ['region=us-east-1']),
        ({'bucket': 'test-bucket', 'dynamodb_table': 'test-table'},
         ['bucket=test-bucket', 'dynamodb_table=test-table']),
        ({'bucket': 'test-bucket', 'dynamodb_table': 'test-table',
          'region': 'us-east-1'},
         ['bucket=test-bucket', 'dynamodb_table=test-table',
          'region=us-east-1']),
        ({'bucket': 'test-bucket', 'dynamodb_table': 'test-table',
          'region': 'us-east-1', 'filename': 'anything'},
         ['bucket=test-bucket', 'dynamodb_table=test-table',
          'region=us-east-1'])
    ])
    def test_init_args(self, input_data, expected_items):
        """Test init_args."""
        expected = []
        for i in expected_items:
            expected.extend(['-backend-config', i])
        assert TerraformBackendConfig(**input_data).init_args == expected

    @pytest.mark.parametrize('kwargs, stack_info,expected', [
        ({'bucket': 'tf-state::BucketName',
          'dynamodb_table': 'tf-state::TableName'},
         {'tf-state': {'BucketName': 'test-bucket', 'TableName': 'test-table'}},
         {'bucket': 'test-bucket', 'dynamodb_table': 'test-table'}),
        ({}, {}, {})
    ])
    def test_resolve_cfn_outputs(self, kwargs, stack_info, expected):
        """Test resolve_cfn_outputs."""
        client = boto3.client('cloudformation')
        stubber = Stubber(client)
        for stack, outputs in stack_info.items():
            for key, val in outputs.items():
                stubber.add_response(
                    'describe_stacks',
                    {
                        'Stacks': [{
                            'StackName': stack,
                            'CreationTime': datetime.now(),
                            'StackStatus': 'CREATE_COMPLETE',
                            'Outputs': [{
                                'OutputKey': key,
                                'OutputValue': val
                            }]
                        }]
                    }
                )
        with stubber:
            assert TerraformBackendConfig.resolve_cfn_outputs(
                client, **kwargs
            ) == expected
        stubber.assert_no_pending_responses()

    @pytest.mark.parametrize('kwargs, parameters, expected', [
        ({'bucket': '/some/param/key', 'dynamodb_table': 'foo'},
         [{'name': '/some/param/key', 'value': 'test-bucket'},
          {'name': 'foo', 'value': 'test-table'}],
         {'bucket': 'test-bucket', 'dynamodb_table': 'test-table'}),
        ({}, {}, {})
    ])
    @pytest.mark.skipif(sys.version_info.major < 3,
                        reason='python 2 dict handling prevents this from '
                        'reliably passing')
    def test_resolve_ssm_params(self, caplog, kwargs, parameters, expected):
        """Test resolve_ssm_params."""
        # this test is not compatable with python 2 due to how it handles dicts
        caplog.set_level('WARNING', logger='runway')

        client = boto3.client('ssm')
        stubber = Stubber(client)

        for param in parameters:
            stubber.add_response(
                'get_parameter',
                {
                    'Parameter': {
                        'Name': param['name'],
                        'Value': param['value'],
                        'LastModifiedDate': datetime.now()
                    }
                },
                {'Name': param['name'], 'WithDecryption': True}
            )

        with stubber:
            assert TerraformBackendConfig.resolve_ssm_params(
                client, **kwargs
            ) == expected
        stubber.assert_no_pending_responses()
        assert 'deprecated' in caplog.records[0].msg

    def test_gen_backend_tfvars_filenames(self):
        """Test gen_backend_tfvars_filenames."""
        expected = ['backend-test-us-east-1.tfvars',
                    'backend-test.tfvars',
                    'backend-us-east-1.tfvars',
                    'backend.tfvars']

        assert TerraformBackendConfig.gen_backend_tfvars_filenames(
            'test', 'us-east-1'
        ) == expected

    @pytest.mark.parametrize('filename, expected', [
        ('backend-test-us-east-1.tfvars', 'backend-test-us-east-1.tfvars'),
        ('backend-test.tfvars', 'backend-test.tfvars'),
        ('backend-us-east-1.tfvars', 'backend-us-east-1.tfvars'),
        ('backend.tfvars', 'backend.tfvars'),
        ('something-backend.tfvars', None),
        (['backend-test-us-east-1.tfvars', 'backend.tfvars'],
         'backend-test-us-east-1.tfvars')
    ])
    def test_get_backend_tfvars_file(self, tmp_path, filename, expected):
        """Test get_backend_tfvars_file."""
        if isinstance(filename, list):
            for name in filename:
                (tmp_path / name).touch()
        else:
            (tmp_path / filename).touch()
        # TODO remove conversion of path to str when dripping python 2
        assert TerraformBackendConfig.get_backend_tfvars_file(
            str(tmp_path), 'test', 'us-east-1'
        ) == expected

    @pytest.mark.parametrize('config, expected_region', [
        ({'terraform_backend_config': {'bucket': 'foo',
                                       'dynamodb_table': 'bar',
                                       'region': 'us-west-2'}}, 'us-west-2'),
        ({'terraform_backend_config': {'region': 'us-west-2'},
          'terraform_backend_cfn_outputs': {'bucket': 'foo',
                                            'dynamodb_table': 'bar'}},
         'us-west-2'),
        ({'terraform_backend_config': {'region': 'us-west-2'},
          'terraform_backend_ssm_params': {'bucket': 'foo',  # deprecated
                                           'dynamodb_table': 'bar'}},
         'us-west-2'),
        ({'terraform_backend_config': {'bucket': 'foo',
                                       'dynamodb_table': 'bar'}},
         'us-east-1'),
        ({'terraform_backend_cfn_outputs': {'bucket': 'foo',
                                            'dynamodb_table': 'bar'}},
         'us-east-1'),
        ({'terraform_backend_ssm_params': {'bucket': 'foo',  # deprecated
                                           'dynamodb_table': 'bar'}},
         'us-east-1'),
        ({'terraform_backend_cfn_outputs': {'bucket': 'foo',
                                            'dynamodb_table': 'bar'}},
         'us-east-1'),
        ({'terraform_backend_ssm_params': {'bucket': 'foo',  # deprecated
                                           'dynamodb_table': 'bar'}},
         'us-east-1'),
        ({'terraform_backend_cfn_outputs': {'bucket': 'foo'},
          'terraform_backend_ssm_params': {'dynamodb_table': 'bar'}},  # deprecated
         'us-east-1'),
        ({'terraform_backend_config': {'bucket': 'nope',
                                       'dynamodb_table': 'nope',
                                       'region': 'us-west-2'},
          'terraform_backend_cfn_outputs': {'bucket': 'foo',
                                            'dynamodb_table': 'bar'}},
         'us-west-2'),
        ({'terraform_backend_config': {'bucket': 'nope',
                                       'dynamodb_table': 'nope',
                                       'region': 'us-west-2'},
          'terraform_backend_ssm_params': {'bucket': 'foo',  # deprecated
                                           'dynamodb_table': 'bar'}},
         'us-west-2'),
        ({'terraform_backend_cfn_outputs': {'bucket': 'nope',
                                            'dynamodb_table': 'nope'},
          'terraform_backend_ssm_params': {'bucket': 'foo',  # deprecated
                                           'dynamodb_table': 'bar'}},
         'us-east-1'),
        ({'terraform_backend_config': {'test': {'bucket': 'foo',  # deprecated
                                                'dynamodb_table': 'bar'},
                                       'prod': {'bucket': 'invalid',
                                                'dynamodb_table': 'invalid'}}},
         'us-east-1')
    ])
    def test_parse(self, monkeypatch, runway_context, config, expected_region):
        """Test parse."""
        runway_context.add_stubber('cloudformation', expected_region)
        runway_context.add_stubber('ssm', expected_region)

        if sys.version_info.major < 3:  # python 2 support
            @staticmethod
            def assert_cfn_kwargs(client, **kwargs):
                """Assert args passed to the method during parse."""
                assert kwargs == config.get('terraform_backend_cfn_outputs')
                return kwargs

            @staticmethod
            def assert_ssm_kwargs(client, **kwargs):
                """Assert args passed to the method during parse."""
                assert kwargs == config.get('terraform_backend_ssm_params')
                return kwargs

            @classmethod
            def assert_get_backend_tfvars_file_args(_, path, env_name, env_region):
                """Assert args passed to the method during parse."""
                assert path == './'
                assert env_name == 'test'
                assert env_region == 'us-east-1'
                return 'success'
        else:
            def assert_cfn_kwargs(client, **kwargs):
                """Assert args passed to the method during parse."""
                assert kwargs == config.get('terraform_backend_cfn_outputs')
                return kwargs

            def assert_ssm_kwargs(client, **kwargs):
                """Assert args passed to the method during parse."""
                assert kwargs == config.get('terraform_backend_ssm_params')
                return kwargs

            def assert_get_backend_tfvars_file_args(path, env_name, env_region):
                """Assert args passed to the method during parse."""
                assert path == './'
                assert env_name == 'test'
                assert env_region == 'us-east-1'
                return 'success'

        monkeypatch.setattr(TerraformBackendConfig, 'resolve_cfn_outputs',
                            assert_cfn_kwargs)
        monkeypatch.setattr(TerraformBackendConfig,
                            'resolve_ssm_params',
                            assert_ssm_kwargs)
        monkeypatch.setattr(TerraformBackendConfig, 'get_backend_tfvars_file',
                            assert_get_backend_tfvars_file_args)

        result = TerraformBackendConfig.parse(runway_context, './', **config)

        assert result.bucket == 'foo'
        assert result.dynamodb_table == 'bar'
        assert result.region == expected_region
        assert result.filename == 'success'
