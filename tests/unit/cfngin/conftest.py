"""Pytest fixtures and plugins."""

# pyright: basic
import os
from pathlib import Path

import pytest

from runway.cfngin.dag import DAG


@pytest.fixture(scope="package")
def cfngin_fixtures() -> Path:
    """CFNgin fixture directory Path object."""
    path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "fixtures")
    return Path(path)


@pytest.fixture
def empty_dag() -> DAG:
    """Create an empty DAG."""
    return DAG()


@pytest.fixture
def basic_dag() -> DAG:
    """Create a basic DAG."""
    dag = DAG()
    dag.from_dict({"a": ["b", "c"], "b": ["d"], "c": ["d"], "d": []})
    return dag
