"""Test runway.cfngin.hooks.awslambda.python_requirements._deployment_package."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from mock import Mock, call

from runway.cfngin.hooks.awslambda.python_requirements import PythonDeploymentPackage

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

MODULE = "runway.cfngin.hooks.awslambda.python_requirements._deployment_package"


class TestPythonDeploymentPackage:
    """Test PythonDeploymentPackage."""

    @pytest.mark.parametrize(
        "slim, strip", [(False, False), (False, True), (True, False), (True, True)]
    )
    def test_gitignore_filter(
        self, mocker: MockerFixture, slim: bool, strip: bool
    ) -> None:
        """Test gitignore_filter."""
        mock_ignore_parser = Mock()
        mock_ignore_parser_class = mocker.patch(
            f"{MODULE}.IgnoreParser", return_value=mock_ignore_parser
        )
        project = Mock(dependency_directory="dependency_directory")
        project.args.slim = slim
        project.args.strip = strip
        if slim:
            assert (
                PythonDeploymentPackage(project).gitignore_filter == mock_ignore_parser
            )
            mock_ignore_parser_class.assert_called_once_with()
            calls = [
                call("**/*.dist-info*", project.dependency_directory),
                call("**/*.py[c|d|i|o]", project.dependency_directory),
                call("**/__pycache__*", project.dependency_directory),
            ]
            if strip:
                calls.append(call("**/*.so", project.dependency_directory))
            mock_ignore_parser.add_rule.assert_has_calls(calls)
        else:
            assert not PythonDeploymentPackage(project).gitignore_filter

    def test_insert_layer_dir(self, tmp_path: Path) -> None:
        """Test insert_layer_dir."""
        assert (
            PythonDeploymentPackage.insert_layer_dir(tmp_path / "foo.txt", tmp_path)
            == tmp_path / "python" / "foo.txt"
        )
        assert (
            PythonDeploymentPackage.insert_layer_dir(
                tmp_path / "bar" / "foo.txt", tmp_path
            )
            == tmp_path / "python" / "bar" / "foo.txt"
        )
