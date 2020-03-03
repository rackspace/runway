"""Pytest fixtures and plugins."""
import os
import sys

import py
import pytest

from runway.cfngin.dag import DAG

if sys.version_info[0] > 2:
    from pathlib import Path  # pylint: disable=E
else:
    from pathlib2 import Path  # pylint: disable=E


@pytest.fixture(scope="package")
def cfngin_fixture_dir():
    """Path to the fixture directory."""
    path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                        'fixtures')
    return py.path.local(path)  # pylint: disable=no-member


@pytest.fixture(scope="package")
def cfngin_fixtures():
    """CFNgin fixture directory Path object."""
    path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                        'fixtures')
    return Path(path)


@pytest.fixture
def empty_dag():
    """Create an empty DAG."""
    return DAG()


@pytest.fixture
def basic_dag():
    """Create a basic DAG."""
    dag = DAG()
    dag.from_dict({'a': ['b', 'c'],
                   'b': ['d'],
                   'c': ['d'],
                   'd': []})
    return dag
