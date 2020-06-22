"""Tests runway/commands/modules_command.py."""
# pylint: disable=no-self-use,protected-access,redefined-outer-name
import datetime
import logging
import os
import sys
from os import path

import boto3
import pytest
import six
import yaml
from botocore.stub import Stubber
from mock import ANY, MagicMock, call, patch

from runway.commands.modules_command import (ModulesCommand,
                                             _deployment_menu_entry,
                                             _module_menu_entry,
                                             _module_name_for_display,
                                             assume_role,
                                             load_module_opts_from_file,
                                             post_deploy_assume_role,
                                             pre_deploy_assume_role,
                                             select_modules_to_run,
                                             validate_account_alias,
                                             validate_account_credentials,
                                             validate_account_id,
                                             validate_environment)
from runway.util import MutableMap, environ

from ..factories import MockBoto3Session

MODULE = 'runway.commands.modules_command'
PATCH_RUNWAY_CONFIG = 'runway.commands.base_command.Config'


@pytest.fixture(scope='function')
def module_tag_config():
    """Return a runway.yml file for testing module tags."""
    fixture_dir = path.join(
        path.dirname(path.dirname(path.realpath(__file__))),
        'fixtures'
    )
    with open(path.join(fixture_dir, 'tag.runway.yml'), 'r') as stream:
        return yaml.safe_load(stream)


@pytest.mark.parametrize('session_name, duration, region, env_vars', [
    (None, None, 'us-east-1', None),
    ('my_session', 900, 'us-west-2', {'AWS_ACCESS_KEY_ID': 'env-var-access-key',
                                      'AWS_SECRET_ACCESS_KEY': 'env-secret-key',
                                      'AWS_SESSION_TOKEN': 'env-session-token'})
])
def test_assume_role(session_name, duration, region, env_vars, caplog, monkeypatch):
    """Test assume_role."""
    caplog.set_level(logging.INFO, logger='runway')
    role_arn = 'arn:aws:iam::123456789012:role/test'
    session = MockBoto3Session(region_name=region)
    _client, stubber = session.register_client('sts')
    monkeypatch.setattr(MODULE + '.boto3', session)

    expected = {'AWS_ACCESS_KEY_ID': 'test-aws-access-key-id',
                'AWS_SECRET_ACCESS_KEY': 'test-secret-key',
                'AWS_SESSION_TOKEN': 'test-session-token'}
    expected_sts_client = {'region_name': region}
    expected_parameters = {'RoleArn': role_arn,
                           'RoleSessionName': session_name or 'runway'}
    if duration:
        expected_parameters['DurationSeconds'] = duration
    if env_vars:
        expected_sts_client.update({k.lower(): v for k, v in env_vars.items()})

    stubber.add_response('assume_role',
                         {'Credentials': {
                             'AccessKeyId': expected['AWS_ACCESS_KEY_ID'],
                             'SecretAccessKey': expected['AWS_SECRET_ACCESS_KEY'],
                             'SessionToken': expected['AWS_SESSION_TOKEN'],
                             'Expiration': datetime.datetime.now()
                         }, 'AssumedRoleUser': {'AssumedRoleId': 'test-role-id',
                                                'Arn': role_arn + '/user'}},
                         expected_parameters)
    with stubber:
        assert assume_role(role_arn, session_name=session_name,
                           duration_seconds=duration, region=region,
                           env_vars=env_vars) == expected
    stubber.assert_no_pending_responses()
    session.assert_client_called_with('sts', **expected_sts_client)
    assert caplog.messages == ["Assuming role %s..." % role_arn]


@pytest.mark.parametrize('deployment, expected', [
    ('min_required', 'deployment_1 - sampleapp-01.cfn (us-east-1)'),
    ('min_required_multi',
     'deployment_1 - sampleapp-01.cfn, sampleapp-02.cfn (us-east-1, us-west-2)')
])
def test_deployment_menu_entry(deployment, expected, fx_deployments):
    """Test _deployment_menu_entry."""
    assert _deployment_menu_entry(fx_deployments.load(deployment)) == expected


def test_load_module_opts_from_file(tmp_path):
    """Test load_module_opts_from_file."""
    mod_opts = {'initial': 'val'}
    file_content = {'file_key': 'file_val'}
    merged = {'file_key': 'file_val', 'initial': 'val'}
    file_path = tmp_path / 'runway.module.yml'

    assert load_module_opts_from_file(str(tmp_path), mod_opts.copy()) == mod_opts

    file_path.write_text(six.u(yaml.safe_dump(file_content)))
    assert load_module_opts_from_file(str(tmp_path), mod_opts.copy()) == merged


@pytest.mark.parametrize('module, expected', [
    ('string', 'string'),
    ({'path': 'simple-dict'}, 'simple-dict'),
    ({'path': 'env-mismatch', 'environments': {'dev': True}}, 'env-mismatch'),
    ({'path': 'env-match', 'environments': {'test': 'something'}},
     'env-match (something)')
])
def test_module_menu_entry(module, expected):
    """Test _module_menu_entry."""
    assert _module_menu_entry(module, 'test') == expected


@pytest.mark.parametrize('module, expected', [
    ({'path': 'path-dict'}, 'path-dict'),
    ('string', 'string'),
    (MagicMock(path='path-attr'), 'path-attr')
])
def test_module_name_for_display(module, expected):
    """Test _module_name_for_display."""
    assert _module_name_for_display(module) == expected


def test_post_deploy_assume_role(monkeypatch, runway_context):
    """Test post_deploy_assume_role."""
    mock_restore = MagicMock()
    monkeypatch.setattr(runway_context, 'restore_existing_iam_env_vars',
                        mock_restore)

    assert not post_deploy_assume_role('test', runway_context)
    mock_restore.assert_not_called()
    assert not post_deploy_assume_role({'key': 'val'}, runway_context)
    mock_restore.assert_not_called()
    assert not post_deploy_assume_role({'post_deploy_env_revert': False},
                                       runway_context)
    mock_restore.assert_not_called()
    assert not post_deploy_assume_role({'post_deploy_env_revert': True},
                                       runway_context)
    mock_restore.assert_called_once()
    assert not post_deploy_assume_role({'post_deploy_env_revert': 'any'},
                                       runway_context)
    assert mock_restore.call_count == 2


@pytest.mark.parametrize('config', [
    ('arn:aws:iam::123456789012:role/test'),
    ({}),
    ({'post_deploy_env_revert': False,
      'arn': 'arn:aws:iam::123456789012:role/test'}),
    ({'post_deploy_env_revert': True,
      'arn': 'arn:aws:iam::123456789012:role/test',
      'duration': 900}),
    ({'post_deploy_env_revert': True,
      'session_name': 'test-custom',
      'arn': 'arn:aws:iam::123456789012:role/test',
      'duration': 900}),
    ({'test': {'arn': 'arn:aws:iam::123456789012:role/test'}}),
    ({'nope': {'arn': 'arn:aws:iam::123456789012:role/test'}}),
    ({'test': 'arn:aws:iam::123456789012:role/test'})
])
def test_pre_deploy_assume_role(config, caplog, monkeypatch, runway_context):
    """Test pre_deploy_assume_role."""
    caplog.set_level(logging.INFO, logger='runway')
    orig_creds = runway_context.boto3_credentials.copy()
    assume_response = {'AWS_ACCESS_KEY_ID': 'assumed_access_key',
                       'AWS_SECRET_ACCESS_KEY': 'assumed_secret_key',
                       'AWS_SESSION_TOKEN': 'assume_session_token'}
    expected_creds = {k.lower(): v for k, v in assume_response.items()}
    mock_save = MagicMock()
    monkeypatch.setattr(runway_context, 'save_existing_iam_env_vars', mock_save)
    runway_context.env_name = 'test'
    mock_assume = MagicMock(return_value=assume_response.copy())
    monkeypatch.setattr(MODULE + '.assume_role', mock_assume)

    assert not pre_deploy_assume_role(config, runway_context)

    if isinstance(config, dict):
        def get_value(key):
            """Get value from config."""
            env_val = config.get(runway_context.env_name)
            result = config.get(key)
            if not result and key == 'arn' and isinstance(env_val, str):
                return env_val
            if not result and isinstance(env_val, dict):
                return env_val.get(key)
            return result

        arn = get_value('arn')
        duration = get_value('duration')

        if arn:
            assert runway_context.boto3_credentials == expected_creds
            mock_assume.assert_called_once_with(role_arn=arn,
                                                session_name=config.get(
                                                    'session_name'
                                                ),
                                                duration_seconds=duration,
                                                region=runway_context.env_region,
                                                env_vars=runway_context.env_vars)
            if config.get('post_deploy_env_revert'):
                mock_save.assert_called_once()
        else:
            mock_assume.assert_not_called()
            assert runway_context.boto3_credentials == orig_creds
            assert caplog.messages == ['Skipping iam:AssumeRole; no role found'
                                       ' for environment test...']
    else:
        assert runway_context.boto3_credentials == expected_creds
        mock_assume.assert_called_once_with(role_arn=config,
                                            region=runway_context.env_region,
                                            env_vars=runway_context.env_vars)


@pytest.mark.parametrize('deployment, kwargs, mock_input, expected', [
    ('min_required', {'ci': True}, None, ['sampleapp-01.cfn']),
    ({'name': 'no_modules'}, {}, None, 1),  # config class makes this obsolete
    ('min_required', {'command': 'deploy'}, None, ['sampleapp-01.cfn']),
    ('min_required', {'command': 'destroy', 'ci': True}, None,
     ['sampleapp-01.cfn']),
    ('min_required', {'command': 'destroy'}, MagicMock(return_value='y'),
     ['sampleapp-01.cfn']),
    ('min_required', {'command': 'destroy'}, MagicMock(return_value='n'), 0),
    ('min_required_multi', {}, MagicMock(return_value='all'),
     ['sampleapp-01.cfn', 'sampleapp-02.cfn']),
    ('min_required_multi', {}, MagicMock(return_value=''), 1),
    ('min_required_multi', {}, MagicMock(return_value='0'), 1),
    ('min_required_multi', {}, MagicMock(return_value='-1'), 1),
    ('min_required_multi', {}, MagicMock(return_value='invalid'), 1),
    ('simple_parallel_module', {'command': 'destroy'},
     MagicMock(side_effect=['1', '2']), ['sampleapp-02.cfn']),
    ('tagged_multi', {'tags': ['app:test-app']}, None,
     ['sampleapp-01.cfn', 'sampleapp-02.cfn', 'sampleapp-03.cfn']),
    ('tagged_multi', {'tags': ['app:test-app', 'tier:iac'], 'ci': True},
     None, ['sampleapp-01.cfn']),
    ('tagged_multi', {'tags': ['no-match']}, None, []),
])
def test_select_modules_to_run(deployment, kwargs, mock_input, expected,
                               fx_deployments, monkeypatch, caplog):
    """Test select_modules_to_run."""
    caplog.set_level(logging.INFO, logger='runway')
    if isinstance(deployment, str):
        deployment = fx_deployments.load(deployment)
    monkeypatch.setattr(MODULE + '.input', mock_input)

    if isinstance(expected, int):
        with pytest.raises(SystemExit) as excinfo:
            assert not select_modules_to_run(deployment, **kwargs)
        assert excinfo.value.code == expected
    else:
        filtered_deployment = select_modules_to_run(deployment, **kwargs)
        result = []
        for mod in filtered_deployment.modules:
            if mod.name == 'parallel_parent':
                result.extend([m.path for m in mod.child_modules])
            else:
                result.append(mod.path)
        assert result == expected

    if mock_input:
        mock_input.assert_called()


def test_validate_account_alias(caplog):
    """Test validate_account_alias."""
    caplog.set_level(logging.INFO, logger='runway')
    alias = 'test-alias'
    iam_client = boto3.client('iam')
    stubber = Stubber(iam_client)

    stubber.add_response('list_account_aliases', {'AccountAliases': [alias]})
    stubber.add_response('list_account_aliases', {'AccountAliases': ['no-match']})

    with stubber:
        assert not validate_account_alias(iam_client, alias)
        with pytest.raises(SystemExit) as excinfo:
            assert validate_account_alias(iam_client, alias)
        assert excinfo.value.code == 1
    stubber.assert_no_pending_responses()
    assert caplog.messages == [
        'Verified current AWS account alias matches required alias {}.'.format(alias),
        'Current AWS account aliases "{}" do not match required account'
        ' alias {} in Runway config.'.format('no-match', alias)
    ]


def test_validate_account_id(caplog):
    """Test validate_account_id."""
    caplog.set_level(logging.INFO, logger='runway')
    account_id = '123456789012'
    arn = 'arn:aws:sts:us-east-1/irrelevant'
    user = 'irrelevant'
    sts_client = boto3.client('sts')
    stubber = Stubber(sts_client)

    stubber.add_response('get_caller_identity', {'UserId': user,
                                                 'Account': account_id,
                                                 'Arn': arn})
    stubber.add_response('get_caller_identity', {'UserId': user,
                                                 'Account': '012345678901',
                                                 'Arn': arn})
    stubber.add_response('get_caller_identity', {'UserId': user,
                                                 'Arn': arn})

    with stubber:
        assert not validate_account_id(sts_client, account_id)
        with pytest.raises(SystemExit) as excinfo:
            assert validate_account_id(sts_client, account_id)
        assert excinfo.value.code == 1
        with pytest.raises(SystemExit) as excinfo:
            assert validate_account_id(sts_client, account_id)
        assert excinfo.value.code == 1
    stubber.assert_no_pending_responses()
    assert caplog.messages == [
        'Verified current AWS account matches required account id %s.' % account_id,
        'Current AWS account 012345678901 does not match required account'
        ' %s in Runway config.' % account_id,
        'Error checking current account ID'
    ]


def test_validate_account_credentials(fx_deployments, monkeypatch,
                                      runway_context):
    """Test validate_account_credentials."""
    mock_alias = MagicMock()
    mock_id = MagicMock()
    account_id = '123456789012'
    alias = 'test'

    # can ignore these
    runway_context.add_stubber('iam')
    runway_context.add_stubber('sts')

    monkeypatch.setattr(MODULE + '.validate_account_alias', mock_alias)
    monkeypatch.setattr(MODULE + '.validate_account_id', mock_id)

    assert not validate_account_credentials(
        fx_deployments.load('min_required'), runway_context)
    mock_alias.assert_not_called()
    mock_id.assert_not_called()

    assert not validate_account_credentials(
        fx_deployments.load('validate_account'), runway_context)
    mock_alias.assert_called_once_with(ANY, alias)
    mock_id.assert_called_once_with(ANY, account_id)

    assert not validate_account_credentials(
        fx_deployments.load('validate_account_map'), runway_context)
    mock_alias.assert_called_with(ANY, alias)
    mock_id.assert_called_with(ANY, account_id)

    mock_alias.reset_mock()
    mock_id.reset_mock()
    runway_context.env_name = 'something-else'

    assert not validate_account_credentials(
        fx_deployments.load('validate_account_map'), runway_context)
    mock_alias.assert_not_called()
    mock_id.assert_not_called()


@pytest.mark.parametrize('env_def, strict, expected, expected_logs', [
    ({'invalid'}, False, False,
     ['test_module: skipped; unsupported type for environments "%s"' % type(set())]),
    (True, False, True, ['test_module: explicitly enabled']),
    (False, False, False, ['test_module: skipped; explicitly disabled']),
    (['123456789012/us-east-1'], False, True, []),
    (['123456789012/us-east-2'], False, False,
     ['test_module: skipped; account_id/region mismatch']),
    ('123456789012/us-east-1', False, True, []),
    ('123456789012/us-east-2', False, False,
     ['test_module: skipped; account_id/region mismatch']),
    ({}, False, None,
     ['test_module: environment not defined; module will determine deployment']),
    ({}, True, None,
     ['test_module: environment not defined; module will determine deployment']),
    ({'example': '111111111111/us-east-1'}, False, None,
     ['test_module: environment not in definition; module will determine deployment']),
    ({'example': '111111111111/us-east-1'}, True, False,
     ['test_module: skipped; environment not in definition']),
    ({'test': False}, False, False,
     ['test_module: skipped; explicitly disabled']),
    ({'test': True}, False, True, ['test_module: explicitly enabled']),
    ({'test': '123456789012/us-east-1'}, False, True, []),
    ({'test': '123456789012/us-east-2'}, False, False,
     ['test_module: skipped; account_id/region mismatch']),
    ({'test': '123456789012'}, False, True, []),
    ({'test': '111111111111'}, False, False,
     ['test_module: skipped; account_id/region mismatch']),
    ({'test': 123456789012}, False, True, []),
    ({'test': 111111111111}, False, False,
     ['test_module: skipped; account_id/region mismatch']),
    ({'test': 'us-east-1'}, False, True, []),
    ({'test': 'us-east-2'}, False, False,
     ['test_module: skipped; account_id/region mismatch']),
    ({'test': ['123456789012/us-east-1', '123456789012/us-east-2']}, False,
     True, []),
    ({'test': ['123456789012/us-east-2']}, False, False,
     ['test_module: skipped; account_id/region mismatch']),
    ({'test': ['123456789012', '111111111111']}, False, True, []),
    ({'test': ['111111111111']}, False, False,
     ['test_module: skipped; account_id/region mismatch']),
    ({'test': [123456789012, 111111111111]}, False, True, []),
    ({'test': [111111111111]}, False, False,
     ['test_module: skipped; account_id/region mismatch']),
    ({'test': ['us-east-1', 'us-east-2']}, False, True, []),
    ({'test': ['us-east-2']}, False, False,
     ['test_module: skipped; account_id/region mismatch'])
])
def test_validate_environment(env_def, strict, expected, expected_logs,
                              caplog, runway_context):
    """Test validate_environment."""
    mock_module = MutableMap(name='test_module')
    caplog.set_level(logging.DEBUG, logger='runway')
    assert validate_environment(runway_context, mock_module, env_def, strict) \
        is expected
    # all() does not give an output that can be used for troubleshooting failures
    for log in expected_logs:
        assert log in caplog.messages


@pytest.mark.usefixtures('patch_runway_config')
class TestModulesCommand(object):
    """Test runway.commands.modules_command.ModulesCommand.

    Protected methods are being patched and tested. While not best practice,
    the logic is too dense not to. It needs to be refactored into smaller
    chunks to be properly tested but, this is a "first pass" so that we
    have some coverage pre-refactor.

    """

    @patch(MODULE + '.validate_environment')
    @patch(MODULE + '.merge_nested_environment_dicts')
    @patch(MODULE + '.Path')
    @patch(MODULE + '.RunwayModuleType')
    @patch(MODULE + '.change_dir')
    @pytest.mark.parametrize('deployment, command, strict, should_validate_env', [
        ('min_required', 'deploy', True, True),
        ('min_required', 'deploy', False, False),
        ('min_required', 'destroy', False, False),
        ('min_required', 'plan', False, False),
        ('validate_account', 'deploy', True, True),
        ('validate_account', 'deploy', False, False),
        ('validate_account', 'destroy', False, False),
        ('validate_account', 'plan', False, False),
        ('simple_env_vars', 'deploy', True, True),
        ('simple_env_vars', 'deploy', False, False),
        ('simple_env_vars', 'destroy', False, False),
        ('simple_env_vars', 'plan', False, False),
        ('simple_env_vars_map', 'deploy', True, True),
        ('simple_env_vars_map', 'deploy', False, False),
        ('simple_env_vars_map', 'destroy', False, False),
        ('simple_env_vars_map', 'plan', False, False),
        ('environments_map_deprecated', 'deploy', True, True),
        ('environments_map_deprecated', 'deploy', False, False),
        ('environments_map_deprecated', 'destroy', False, False),
        ('environments_map_deprecated', 'plan', False, False),
        ('environments_map_list', 'deploy', True, True),
        ('environments_map_list', 'deploy', False, True),
        ('environments_map_list', 'destroy', False, True),
        ('environments_map_list', 'plan', False, True),
        ('environments_map_str', 'deploy', True, True),
        ('environments_map_str', 'deploy', False, True),
        ('environments_map_str', 'destroy', False, True),
        ('environments_map_str', 'plan', False, True),
    ])
    def test_deploy_module(self, mock_change_dir, mock_runwaymoduletype,
                           mock_path,
                           mock_merge_nested_environment_dicts,
                           mock_validate_environment,
                           deployment, command, strict, should_validate_env,
                           fx_deployments, monkeypatch, runway_context,
                           patch_runway_config):
        """Test _deploy_module.

        This test is not well designed but it is about as good as it can be
        given the density of logic and branches in the corresponding method.

        """
        deployment = fx_deployments.load(deployment)
        module = deployment.modules[0]
        runway_context.command = command
        mock_module_instance = MagicMock()
        patch_runway_config.future.strict_environments = strict

        mock_runwaymoduletype.return_value = mock_runwaymoduletype
        mock_runwaymoduletype.module_class.return_value = mock_module_instance

        monkeypatch.setattr(deployment, 'resolve', MagicMock())
        monkeypatch.setattr(module, 'resolve', MagicMock())
        monkeypatch.setattr(MODULE + '.load_module_opts_from_file',
                            lambda x, y: y)  # return module_opts

        assert not ModulesCommand()._deploy_module(module, deployment,
                                                   runway_context)
        # second arg should be a mock
        deployment.resolve.assert_called_once_with(runway_context, ANY)
        deployment.resolve.assert_called_once_with(runway_context, ANY)
        mock_path.assert_called_once_with(module, os.getcwd(),
                                          os.path.join(os.getcwd(),
                                          '.runway_cache'))
        if deployment.env_vars or module.env_vars:
            mock_merge_nested_environment_dicts.assert_called_once_with(
                ANY, env_name=runway_context.env_name, env_root=os.getcwd()
            )  # ANY is a dict constructed during execution
            mock_runwaymoduletype.module_class.assert_called_once_with(
                context=ANY,  # context object is altered if env_vars
                path=mock_path().module_root,
                options=ANY  # dict constructed during execution
            )
        else:
            mock_merge_nested_environment_dicts.assert_not_called()
            mock_runwaymoduletype.module_class.assert_called_once_with(
                context=runway_context,
                path=mock_path().module_root,
                options=ANY  # dict constructed during execution
            )
        if should_validate_env:
            mock_validate_environment.assert_called_once_with(
                # second arg is constructed during execution
                context=ANY,  # potentially changed runway_context
                env_def=ANY,  # merged dict of environments
                module=module,
                strict=strict
            )
        else:
            mock_validate_environment.assert_not_called()
        mock_change_dir.assert_has_calls([call(mock_path().module_root),
                                          call().__enter__(),
                                          call().__exit__(None, None, None)])
        # last two args come from module_opts
        mock_runwaymoduletype.assert_called_once_with(mock_path().module_root,
                                                      ANY, ANY)
        mock_module_instance[command].assert_called_once_with()

    @patch(MODULE + '.validate_environment')
    @patch(MODULE + '.RunwayModuleType')
    def test_deploy_module_invalid_env(self, mock_runwaymoduletype,
                                       mock_validate_environment,
                                       fx_deployments, monkeypatch,
                                       runway_context):
        """Test _deploy_module where validate_environment fails."""
        deployment = fx_deployments.load('environments_map_str')
        module = deployment.modules[0]

        monkeypatch.setattr(deployment, 'resolve', MagicMock())
        monkeypatch.setattr(module, 'resolve', MagicMock())
        monkeypatch.setattr(MODULE + '.load_module_opts_from_file',
                            lambda x, y: y)  # return module_opts
        mock_validate_environment.return_value = False

        assert not ModulesCommand()._deploy_module(module, deployment,
                                                   runway_context)
        mock_validate_environment.assert_called_once()
        mock_runwaymoduletype.assert_not_called()

    @patch(MODULE + '.hasattr')
    def test_deploy_module_missing_method(self, mock_hasattr,
                                          fx_deployments, monkeypatch,
                                          runway_context):
        """Test _deploy_module where the command method is missing."""
        deployment = fx_deployments.load('min_required')
        module = deployment.modules[0]

        mock_hasattr.return_value = False
        monkeypatch.setattr(deployment, 'resolve', MagicMock())
        monkeypatch.setattr(module, 'resolve', MagicMock())
        monkeypatch.setattr(MODULE + '.load_module_opts_from_file',
                            lambda x, y: y)  # return module_opts
        monkeypatch.setattr(MODULE + '.change_dir', MagicMock())

        with pytest.raises(SystemExit) as excinfo:
            assert ModulesCommand()._deploy_module(module, deployment,
                                                   runway_context)
        assert excinfo.value.code == 1
        # ANY is a child mock
        mock_hasattr.assert_called_once_with(ANY, runway_context.command)

    def test_execute(self):
        """Test execute."""
        with pytest.raises(NotImplementedError):
            ModulesCommand().execute()

    @patch(MODULE + '.pre_deploy_assume_role')
    @patch(MODULE + '.validate_account_credentials')
    @patch(MODULE + '.post_deploy_assume_role')
    @pytest.mark.parametrize('deployment, region, parallel', [
        ('min_required', 'us-west-2', False),
        ('min_required', 'us-west-2', True),
        ('validate_account', 'us-west-2', False),
        ('validate_account', 'us-west-2', True),
        ('simple_assume_role', 'us-west-2', False),
        ('simple_assume_role', 'us-west-2', True)
    ])
    def test_execute_deployment(self, mock_post_deploy_assume_role,
                                mock_validate_account_credentials,
                                mock_pre_deploy_assume_role,
                                deployment, region, parallel,
                                fx_deployments, monkeypatch, runway_context):
        """Test _execute_deployment."""
        # pylint: disable=no-member
        deployment = fx_deployments.load(deployment)
        monkeypatch.setattr(ModulesCommand, '_process_modules', MagicMock())

        assert not ModulesCommand()._execute_deployment(deployment,
                                                        runway_context,
                                                        region, parallel)
        ModulesCommand._process_modules.assert_called_once_with(
            deployment,
            # context will be a new instance if parallel
            runway_context if not parallel else ANY
        )

        if parallel:
            assert runway_context.env_region == 'us-east-1'
        else:
            assert runway_context.env_region == region
            assert runway_context.env_vars['AWS_DEFAULT_REGION'] == region
            assert runway_context.env_vars['AWS_REGION'] == region

        if deployment.assume_role:
            mock_pre_deploy_assume_role.assume_called_once_with(
                deployment.assume_role,
                # context will be a new instance if parallel
                runway_context if not parallel else ANY
            )
            mock_post_deploy_assume_role.assume_called_once_with(
                deployment.assume_role,
                # context will be a new instance if parallel
                runway_context if not parallel else ANY
            )
        if deployment.account_id or deployment.account_alias:
            mock_validate_account_credentials.assert_called_once_with(
                deployment,
                # context will be a new instance if parallel
                runway_context if not parallel else ANY
            )

    @patch(MODULE + '.merge_dicts')
    @patch(MODULE + '.merge_nested_environment_dicts')
    def test_process_deployments(self, mock_merge_nested_environment_dicts,
                                 mock_merge_dicts, fx_config, monkeypatch,
                                 runway_context):
        """Test _process_deployments."""
        config = fx_config.load('min_required')  # single deployment for tests
        deployment = config.deployments[0]
        monkeypatch.setattr(deployment, 'resolve', MagicMock())
        monkeypatch.setattr(ModulesCommand, 'runway_config', config)
        monkeypatch.setattr(ModulesCommand, '_execute_deployment', MagicMock())

        ModulesCommand()._process_deployments(config.deployments,
                                              runway_context)

        deployment.resolve.assert_called_once_with(runway_context,
                                                   config.variables,
                                                   pre_process=True)
        # pylint: disable=no-member
        ModulesCommand._execute_deployment.assert_has_calls([
            call(deployment, runway_context, region)
            for region in deployment.regions
        ])
        mock_merge_nested_environment_dicts.assert_not_called()
        mock_merge_dicts.assert_not_called()

        copy_env_vars = runway_context.env_vars.copy()
        deployment._env_vars = MagicMock()
        deployment._env_vars.value = {'key': 'val'}
        mock_merge_nested_environment_dicts.return_value = {'state': 'env'}
        mock_merge_dicts.return_value = {'state': 'merged'}
        ModulesCommand()._process_deployments(config.deployments,
                                              runway_context)
        mock_merge_nested_environment_dicts.assert_called_once_with(
            {'key': 'val'},
            env_name=runway_context.env_name,
            env_root=os.getcwd()
        )
        mock_merge_dicts.assert_called_once_with(copy_env_vars,
                                                 {'state': 'env'})
        assert runway_context.env_vars == {'state': 'merged'}
        assert ModulesCommand._execute_deployment.call_count == 2

        ModulesCommand._execute_deployment.reset_mock()
        deployment.modules = []
        ModulesCommand({'--tag': ['something']})._process_deployments(
            config.deployments,
            runway_context
        )
        ModulesCommand._execute_deployment.assert_not_called()

        config = fx_config.load('min_required')
        deployment = config.deployments[0]
        monkeypatch.setattr(deployment, 'resolve', MagicMock())
        deployment._regions = MagicMock()
        deployment._regions.value = []
        with pytest.raises(SystemExit) as excinfo:
            ModulesCommand()._process_deployments(config.deployments,
                                                  runway_context)
        assert excinfo.value.code == 1

    @patch('runway.commands.modules_command.concurrent.futures')
    @pytest.mark.skipif(sys.version_info.major < 3,
                        reason='only supported by python 3')
    @pytest.mark.parametrize('config, use_concurrent', [
        ('simple_parallel_regions.1', True),
        ('simple_parallel_regions.1', False),
        ('simple_parallel_regions.2', True),
        ('simple_parallel_regions.2', False)
    ])
    def test_process_deployments_parallel(self, mock_futures,
                                          config, use_concurrent,
                                          fx_config, monkeypatch,
                                          runway_context):
        """Test _process_deployments with parallel regions."""
        # pylint: disable=no-member
        config = fx_config.load(config)  # single deployment for tests
        deployment = config.deployments[0]
        executor = MagicMock()
        mock_futures.ProcessPoolExecutor.return_value = executor
        runway_context.use_concurrent = use_concurrent
        monkeypatch.setattr(deployment, 'resolve', MagicMock())
        monkeypatch.setattr(ModulesCommand, 'runway_config', config)
        monkeypatch.setattr(ModulesCommand, '_execute_deployment', MagicMock())

        ModulesCommand()._process_deployments(config.deployments,
                                              runway_context)

        deployment.resolve.assert_called_once_with(runway_context,
                                                   config.variables,
                                                   pre_process=True)

        if not use_concurrent:
            ModulesCommand._execute_deployment.assert_called()
            return

        mock_futures.ProcessPoolExecutor.assert_called_once_with(
            max_workers=runway_context.max_concurrent_regions
        )
        executor.submit.has_calls([
            (ModulesCommand._execute_deployment, deployment, runway_context,
             region, True) for region in deployment.parallel_regions
        ])
        mock_futures.wait.called_once()
        assert executor.submit.return_value.result.call_count == \
            len(deployment.parallel_regions)

    @pytest.mark.parametrize('deployment', [('min_required'),
                                            ('min_required_multi')])
    def test_process_modules(self, deployment, fx_deployments, monkeypatch,
                             runway_context):
        """Test _process_modules."""
        # pylint: disable=no-member
        deployment = fx_deployments.load(deployment)
        monkeypatch.setattr(ModulesCommand, '_deploy_module', MagicMock())

        assert not ModulesCommand()._process_modules(deployment, runway_context)
        ModulesCommand._deploy_module.assert_has_calls([
            call(module, deployment, runway_context)
            for module in deployment.modules
        ])

    @patch('runway.commands.modules_command.concurrent.futures')
    @pytest.mark.skipif(sys.version_info.major < 3,
                        reason='only supported by python 3')
    @pytest.mark.parametrize('deployment, use_concurrent', [
        ('simple_parallel_module', True),
        ('simple_parallel_module', False),
    ])
    def test_process_modules_parallel(self, mock_futures, deployment,
                                      use_concurrent, fx_deployments,
                                      monkeypatch, runway_context):
        """Test _process_modules with parallel regions."""
        # pylint: disable=no-member
        deployment = fx_deployments.load(deployment)
        executor = MagicMock()
        mock_futures.ProcessPoolExecutor.return_value = executor
        runway_context.use_concurrent = use_concurrent

        monkeypatch.setattr(ModulesCommand, '_deploy_module', MagicMock())

        assert not ModulesCommand()._process_modules(deployment, runway_context)
        if use_concurrent:
            mock_futures.ProcessPoolExecutor.assert_called_once_with(
                max_workers=runway_context.max_concurrent_modules
            )
            executor.submit.assert_has_calls([
                call(ModulesCommand._deploy_module, x, deployment,
                     runway_context)
                for x in deployment.modules[0].child_modules
            ])
            mock_futures.wait.assert_called_once()
            assert executor.submit.return_value.result.call_count == \
                len(deployment.modules[0].child_modules)
            ModulesCommand._deploy_module.assert_called_once_with(
                deployment.modules[1],
                deployment,
                runway_context
            )
        else:
            ModulesCommand._deploy_module.assert_has_calls([
                call(module, deployment, runway_context)
                for module in deployment.modules[0].child_modules
            ] + [call(deployment.modules[1], deployment, runway_context)])

    def test_reverse_deployments(self, fx_deployments, monkeypatch):
        """Test reverse_deployments."""
        deployment = fx_deployments.load('min_required')
        monkeypatch.setattr(deployment, 'reverse', MagicMock())
        mock_deployments = MagicMock()
        mock_deployments.__iter__.return_value = iter([deployment])

        assert ModulesCommand.reverse_deployments(None) == []
        assert ModulesCommand.reverse_deployments(mock_deployments)
        mock_deployments.reverse.assert_called_once()
        deployment.reverse.assert_called_once()

    @patch(MODULE + '.select_modules_to_run')
    @patch(MODULE + '.get_env')
    @patch(MODULE + '.Context')
    @pytest.mark.parametrize('config, command, cli_args, mock_input', [
        ('min_required', 'deploy', {}, None),
        ('min_required', 'destroy', {}, None),
        ('min_required', 'plan', {}, None),
        ('min_required', 'deploy', {'--tag': ['something']}, None),
        ('min_required', 'destroy', {'--tag': ['something']}, None),
        ('min_required', 'plan', {'--tag': ['something']}, None),
        ('min_required', 'deploy', {}, MagicMock(return_value='y')),
        ('min_required', 'destroy', {}, MagicMock(return_value='y')),
        ('min_required', 'plan', {}, MagicMock(return_value='y')),
        ('min_required', 'deploy', {'--tag': ['something']},
         MagicMock(return_value='y')),
        ('min_required', 'destroy', {'--tag': ['something']},
         MagicMock(return_value='y')),
        ('min_required', 'plan', {'--tag': ['something']},
         MagicMock(return_value='y')),
        ('min_required', 'deploy', {}, MagicMock(return_value='n')),
        ('min_required', 'destroy', {}, MagicMock(return_value='n')),
        ('min_required', 'plan', {}, MagicMock(return_value='n')),
        ('min_required', 'deploy', {'--tag': ['something']},
         MagicMock(return_value='n')),
        ('min_required', 'destroy', {'--tag': ['something']},
         MagicMock(return_value='n')),
        ('min_required', 'plan', {'--tag': ['something']},
         MagicMock(return_value='n'))
    ])
    def test_run(self, mock_context, mock_get_env, mock_select_modules_to_run,
                 config, command, cli_args, mock_input,
                 fx_config, monkeypatch):
        """Test run."""
        config = fx_config.load(config)
        config.future.strict_environments = True

        mock_get_env.return_value = 'test'
        mock_context.return_value = mock_context
        mock_context.is_interactive = bool(mock_input)
        mock_context.is_noninteractive = not bool(mock_input)  # True if None
        mock_context.env_vars = {}

        monkeypatch.setattr(MODULE + '.input', mock_input)
        monkeypatch.setattr(ModulesCommand, 'reverse_deployments',
                            MagicMock(return_value=['reversed-deployments']))
        monkeypatch.setattr(ModulesCommand, 'runway_config', config)
        monkeypatch.setattr(ModulesCommand, 'select_deployment_to_run',
                            MagicMock(return_value=['deployment']))
        monkeypatch.setattr(ModulesCommand, '_process_deployments', MagicMock())

        if command == 'destroy' and mock_input and mock_input.return_value != 'y':
            with pytest.raises(SystemExit) as excinfo:
                ModulesCommand(cli_args).run(command=command)
            mock_input.assert_called_once_with('Proceed?: ')
            assert excinfo.value.code == 0
            return  # end here since a lot of the rest will be skipped

        env_vars = {}
        if not mock_input:
            env_vars['CI'] = '1'

        with environ(env_vars):
            ModulesCommand(cli_args).run(command=command)

            mock_get_env.assert_called_once_with(
                os.getcwd(), config.ignore_git_branch,
                prompt_if_unexpected=bool(mock_input)
            )
            mock_context.assert_called_once_with(env_name='test',
                                                 env_region=None,
                                                 env_root=os.getcwd(),
                                                 env_vars=os.environ,
                                                 command=command)

        assert mock_context.env_vars['RUNWAYCONFIG'] == './runway.yml'

        if command == 'destroy' and mock_input:
            mock_input.assert_called_once_with('Proceed?: ')
            ModulesCommand.reverse_deployments.assert_called_once()

        if mock_context.is_noninteractive or cli_args.get('--tag'):
            mock_select_modules_to_run.assert_called()
        else:
            ModulesCommand.select_deployment_to_run.assert_called_once_with(
                config.deployments, command)
            mock_select_modules_to_run.assert_called_once_with(
                'deployment', cli_args.get('--tag'), command,
                mock_context.is_noninteractive, mock_context.env_name
            )
        # pylint: disable=no-member
        ModulesCommand._process_deployments.assert_called_once_with(ANY,
                                                                    mock_context)

    @pytest.mark.parametrize('config, command, mock_input, expected', [
        ('min_required', 'build', None, ['deployment_1']),
        ('min_required', 'destroy', None, ['deployment_1']),
        ('min_required_multi', 'deploy', MagicMock(return_value='1'),
         ['deployment_1']),
        ('min_required_multi', 'destroy', MagicMock(return_value='1'),
         ['deployment_1']),
        ('min_required_multi', 'deploy', MagicMock(return_value='2'),
         ['deployment_2']),
        ('min_required_multi', 'destroy', MagicMock(return_value='2'),
         ['deployment_2']),
        ('min_required_multi', 'deploy', MagicMock(return_value='all'),
         ['deployment_1', 'deployment_2']),
        ('min_required_multi', 'destroy', MagicMock(return_value='all'),
         ['deployment_1', 'deployment_2']),
        ('min_required_multi', 'deploy', MagicMock(return_value=''), 1),
        ('min_required_multi', 'destroy', MagicMock(return_value=''), 1),
    ])
    def test_select_deployment_to_run(self, config, command, mock_input, expected,
                                      fx_config, monkeypatch):
        """Test select_deployment_to_run."""
        config = fx_config.load(config)
        monkeypatch.setattr(MODULE + '.input', mock_input)

        assert ModulesCommand.select_deployment_to_run([], command) == []

        if isinstance(expected, int):
            with pytest.raises(SystemExit) as excinfo:
                assert not ModulesCommand.select_deployment_to_run(
                    config.deployments,
                    command
                )
            assert excinfo.value.code == expected
        else:
            result = ModulesCommand.select_deployment_to_run(
                config.deployments,
                command
            )
            assert [r.name for r in result] == expected
        if mock_input:
            mock_input.assert_called_once_with(
                'Enter number of deployment to run (or "all"): '
            )
