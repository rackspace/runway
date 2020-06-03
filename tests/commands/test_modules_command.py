"""Tests runway/commands/modules_command.py."""
# pylint: disable=no-self-use,protected-access,redefined-outer-name
import datetime
import logging
import os
from os import path

import boto3
import pytest
import six
import yaml
from botocore.stub import Stubber
from mock import ANY, MagicMock, patch
from moto import mock_sts

from runway.commands.modules_command import (ModulesCommand, assume_role,
                                             load_module_opts_from_file,
                                             post_deploy_assume_role,
                                             pre_deploy_assume_role,
                                             select_modules_to_run,
                                             validate_account_alias,
                                             validate_account_credentials,
                                             validate_account_id,
                                             validate_environment)
from runway.util import environ

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


def test_load_module_opts_from_file(tmp_path):
    """Test load_module_opts_from_file."""
    mod_opts = {'initial': 'val'}
    file_content = {'file_key': 'file_val'}
    merged = {'file_key': 'file_val', 'initial': 'val'}
    file_path = tmp_path / 'runway.module.yml'

    assert load_module_opts_from_file(str(tmp_path), mod_opts.copy()) == mod_opts

    file_path.write_text(six.u(yaml.safe_dump(file_content)))
    assert load_module_opts_from_file(str(tmp_path), mod_opts.copy()) == merged


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


@pytest.mark.usefixtures('patch_runway_config')
class TestModulesCommand(object):
    """Test runway.commands.modules_command.ModulesCommand.

    Protected methods are being patched and tested. While not best practice,
    the logic is too dense not to. It needs to be refactored into smaller
    chunks to be properly tested but, this is a "first pass" so that we
    have some coverage pre-refactor.

    """

    @pytest.mark.wip
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
