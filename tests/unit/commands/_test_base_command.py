"""Test runway.commands.base_command."""
# pylint: disable=no-self-use,protected-access
import os

import pytest
from mock import call

from runway.commands.base_command import BaseCommand
from runway.util import MutableMap

MODULE = 'runway.commands.base_command'
PATCH_RUNWAY_CONFIG = MODULE + '.Config'


class TestBaseCommand(object):
    """Test runway.commands.base_command.BaseCommand."""

    def test_class_attributes(self):
        """Test class attributes."""
        assert BaseCommand.SKIP_FIND_CONFIG is False
        # wording of the message does not have to be exact
        assert 'deprecated' in BaseCommand.DEPRECATION_MSG
        assert 'next major release' in BaseCommand.DEPRECATION_MSG

    def test_execute(self, patch_runway_config):
        """Test execute."""
        patch_runway_config.find_config_file.return_value = 'runway.yml'
        with pytest.raises(NotImplementedError) as excinfo:
            assert BaseCommand(env_root='./',
                               runway_config_dir='./').execute()
        assert str(excinfo.value) == \
            'execute must be implimented for subclasses of BaseCommand.'

    def test_init(self, patch_runway_config):
        """Test init and the attributes it sets."""
        cli_args = {
            '--tag': ['something']
        }
        runway_yml = os.path.join(os.getcwd(), 'runway.yml')
        patch_runway_config.find_config_file.return_value = runway_yml
        obj = BaseCommand(cli_args)

        assert obj._cli_arguments == cli_args
        assert obj._runway_config is None
        assert obj.env_root == os.getcwd()
        assert obj.runway_config_path == runway_yml
        patch_runway_config.find_config_file \
            .assert_called_once_with(os.getcwd())

    def test_init_args_optional(self, patch_runway_config, tmp_path):
        """Test init optional args."""
        runway_config_dir = tmp_path / 'some_dir'
        runway_yml = str(runway_config_dir / 'runway.yml')
        patch_runway_config.find_config_file.return_value = runway_yml
        obj = BaseCommand(env_root=str(tmp_path),
                          runway_config_dir=str(runway_config_dir))

        assert obj._cli_arguments == {}
        assert obj._runway_config is None
        assert obj.env_root == str(tmp_path)
        assert obj.runway_config_path == runway_yml
        patch_runway_config.find_config_file \
            .assert_called_once_with(str(runway_config_dir))

    def test_init_exception_systemexit(self, patch_runway_config):
        """Test init SystemExit raised by Config."""
        cwd = os.getcwd()
        cwd_parent = os.path.dirname(cwd)
        env_root = os.path.join(cwd, 'tests')
        patch_runway_config.find_config_file.side_effect = [SystemExit,
                                                            'runway.yml']
        obj = BaseCommand(env_root=env_root)

        assert obj.runway_config_path == 'runway.yml'
        assert obj.env_root == cwd_parent
        patch_runway_config.find_config_file.assert_has_calls([call(env_root),
                                                               call(cwd_parent)])

    def test_init_skip_find_config(self, monkeypatch, patch_runway_config):
        """Test init where SKIP_FIND_CONFIG=True (subclasses)."""
        monkeypatch.setattr(BaseCommand, 'SKIP_FIND_CONFIG', True)
        obj = BaseCommand()

        assert obj._runway_config is None
        assert obj.runway_config_path is None
        patch_runway_config.find_config_file.assert_not_called()

    def test_runway_config(self, patch_runway_config):
        """Test runway config."""
        obj = BaseCommand()
        assert obj.runway_config == patch_runway_config
        # ensure value is properly cached
        assert obj._runway_config == obj.runway_config
        patch_runway_config.load_from_file \
            .assert_called_once_with('./runway.yml')

    def test_runway_vars(self, patch_runway_config):
        """Test runway_vars."""
        obj = BaseCommand()
        assert isinstance(obj.runway_config, MutableMap)
        assert obj.runway_vars.data == {}
        patch_runway_config.load_from_file.assert_called_once()
