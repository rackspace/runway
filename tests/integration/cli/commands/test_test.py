"""Test ``runway test``."""
import logging

import six
import yaml
from click.testing import CliRunner

from runway._cli import cli

SUCCESS = {
    'name': 'success',
    'type': 'script',
    'args': {
        'commands': ['echo "Hello world"']
    }
}
FAIL = {
    'name': 'fail',
    'type': 'script',
    'required': False,
    'args': {
        'command': ['exit 1']
    }
}
FAIL_REQUIRED = {
    'name': 'fail-required',
    'type': 'script',
    'required': True,
    'args': {
        'command': ['exit 1']
    }
}
INVALID_TYPE = {
    'name': 'invalid-type',
    'type': 'invalid',
    'required': False
}
INVALID_TYPE_REQUIRED = {
    'name': 'invalid-type-required',
    'type': 'invalid',
    'required': True
}


def test_test_invalid_type(cd_tmp_path, capfd, caplog):
    """Test ``runway test`` with two tests; one invalid."""
    caplog.set_level(logging.INFO, logger='runway.core')
    runway_yml = cd_tmp_path / 'runway.yml'
    runway_yml.write_text(six.u(yaml.safe_dump({'deployments': [],
                                                'tests': [INVALID_TYPE.copy(),
                                                          SUCCESS.copy()]})))

    runner = CliRunner()
    result = runner.invoke(cli, ['test'])
    assert result.exit_code == 1

    captured = capfd.readouterr()
    logs = '\n'.join(caplog.messages)
    assert 'Found 2 test(s)' in logs
    assert "Running test 'invalid-type'" in logs
    assert 'Unable to find handler for test "invalid-type" of type "invalid"' in logs
    assert "Running test 'success'" in logs
    assert 'Hello world' in captured.out
    assert 'The following tests failed: invalid-type' in logs


def test_test_invalid_type_required(cd_tmp_path, capfd, caplog):
    """Test ``runway test`` with two tests; one invalid required."""
    caplog.set_level(logging.INFO, logger='runway.core')
    runway_yml = cd_tmp_path / 'runway.yml'
    runway_yml.write_text(six.u(yaml.safe_dump({'deployments': [],
                                                'tests': [INVALID_TYPE_REQUIRED.copy(),
                                                          SUCCESS.copy()]})))

    runner = CliRunner()
    result = runner.invoke(cli, ['test'])
    assert result.exit_code == 1

    captured = capfd.readouterr()
    logs = '\n'.join(caplog.messages)
    assert 'Found 2 test(s)' in logs
    assert "Running test 'invalid-type-required'" in logs
    assert 'Unable to find handler for test "invalid-type-required" of type "invalid"' in logs
    assert "Running test 'success'" not in logs
    assert 'Hello world' not in captured.out


def test_test_not_defined(cd_tmp_path, caplog):
    """Test ``runway test`` with no tests defined."""
    caplog.set_level(logging.ERROR, logger='runway')
    runway_yml = cd_tmp_path / 'runway.yml'
    runway_yml.write_text(six.u(yaml.safe_dump({'deployments': []})))

    runner = CliRunner()
    result = runner.invoke(cli, ['test'])
    assert result.exit_code == 1
    assert 'without defining tests in the runway config' in caplog.messages[0]


def test_test_single_successful(cd_tmp_path, capfd, caplog):
    """Test ``runway test`` with a single, successful test."""
    caplog.set_level(logging.INFO, logger='runway.core')
    runway_yml = cd_tmp_path / 'runway.yml'
    runway_yml.write_text(six.u(yaml.safe_dump({'deployments': [],
                                                'tests': [SUCCESS.copy()]})))

    runner = CliRunner()
    result = runner.invoke(cli, ['test'])
    assert result.exit_code == 0

    captured = capfd.readouterr()
    logs = '\n'.join(caplog.messages)
    assert 'Found 1 test(s)' in logs
    assert "Running test 'success'" in logs
    assert 'Hello world' in captured.out


def test_test_two_test(cd_tmp_path, capfd, caplog):
    """Test ``runway test`` with two tests; one failing."""
    caplog.set_level(logging.INFO, logger='runway.core')
    runway_yml = cd_tmp_path / 'runway.yml'
    runway_yml.write_text(six.u(yaml.safe_dump({'deployments': [],
                                                'tests': [FAIL.copy(),
                                                          SUCCESS.copy()]})))

    runner = CliRunner()
    result = runner.invoke(cli, ['test'])
    assert result.exit_code == 1

    captured = capfd.readouterr()
    logs = '\n'.join(caplog.messages)
    assert 'Found 2 test(s)' in logs
    assert "Running test 'fail'" in logs
    assert 'Test failed: fail' in logs
    assert "Running test 'success'" in logs
    assert 'Hello world' in captured.out
    assert 'The following tests failed: fail' in logs


def test_test_two_test_required(cd_tmp_path, capfd, caplog):
    """Test ``runway test`` with two tests; one failing required."""
    caplog.set_level(logging.INFO, logger='runway.core')
    runway_yml = cd_tmp_path / 'runway.yml'
    runway_yml.write_text(six.u(yaml.safe_dump({'deployments': [],
                                                'tests': [FAIL_REQUIRED.copy(),
                                                          SUCCESS.copy()]})))

    runner = CliRunner()
    result = runner.invoke(cli, ['test'])
    assert result.exit_code == 1

    captured = capfd.readouterr()
    logs = '\n'.join(caplog.messages)
    assert 'Found 2 test(s)' in logs
    assert "Running test 'fail-required'" in logs
    assert 'Test failed: fail-required' in logs
    assert 'Failed test was required, the remaining tests have been skipped' in logs
    assert "Running test 'success'" not in logs
    assert 'Hello world' not in captured.out
