"""Test runway.dependency_managers.base_classes."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from mock import Mock

from runway.dependency_managers.base_classes import DependencyManager

if TYPE_CHECKING:
    from pathlib import Path

    from runway.context import CfnginContext

MODULE = "runway.dependency_managers.base_classes"


class TestDependencyManager:
    """Test DependencyManager."""

    def test___init__(self, cfngin_context: CfnginContext, tmp_path: Path) -> None:
        """Test __init__."""
        obj = DependencyManager(cfngin_context, tmp_path)
        assert obj.ctx == cfngin_context
        assert obj.cwd == tmp_path

    def test_dir_is_project(self, tmp_path: Path) -> None:
        """Test dir_is_project."""
        with pytest.raises(NotImplementedError):
            assert DependencyManager.dir_is_project(tmp_path)

    def test_version(self, tmp_path: Path) -> None:
        """Test version."""
        with pytest.raises(NotImplementedError):
            assert DependencyManager(Mock(), tmp_path).version
