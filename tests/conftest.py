"""Pytest fixtures and plugins."""
from typing import Dict

import logging
import os

import pytest
import yaml

logger = logging.getLogger(__name__)


@pytest.fixture(scope='session', autouse=True)
def aws_credentials():
    # type: () -> Dict[str, str]
    """Handle change in https://github.com/spulec/moto/issues/1924.
    Ensure AWS SDK finds some (bogus) credentials in the environment and
    doesn't try to use other providers.
    """
    overrides = {
        'AWS_ACCESS_KEY_ID': 'testing',
        'AWS_SECRET_ACCESS_KEY': 'testing',
        'AWS_DEFAULT_REGION': 'us-east-1'
    }
    saved_env = {}
    for key, value in overrides.items():
        logger.info('Overriding env var: {}={}'.format(key, value))
        saved_env[key] = os.environ.get(key, None)
        os.environ[key] = value

    yield

    for key, value in saved_env.items():
        logger.info('Restoring saved env var: {}={}'.format(key, value))
        if value is None:
            del os.environ[key]
        else:
            os.environ[key] = value

    saved_env.clear()


@pytest.fixture(scope='package')
def fixture_dir():
    # type: () -> str
    """Path to the fixture directory."""
    path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                        'fixtures')
    return path


@pytest.fixture(scope='module')
def yaml_fixtures(request, fixture_dir):  # pylint: disable=redefined-outer-name
    """Load test fixture yaml files.
    Uses a list of file paths within the fixture directory loaded from the
    `YAML_FIXTURES` variable of the module.
    """
    file_paths = getattr(request.module, 'YAML_FIXTURES', [])
    result = {}
    for file_path in file_paths:
        with open(os.path.join(fixture_dir, file_path)) as f:
            data = f.read()
            result[file_path] = yaml.safe_load(data)
    return result
