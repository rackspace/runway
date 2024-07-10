"""Test runway.cfngin.hooks.awslambda.python_requirements._docker."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

import pytest
from docker.types.services import Mount
from mock import Mock

from runway.cfngin.hooks.awslambda.python_requirements import (
    PythonDockerDependencyInstaller,
)
from runway.utils import Version

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

MODULE = "runway.cfngin.hooks.awslambda.python_requirements._docker"


class TestPythonDockerDependencyInstaller:
    """Test PythonDockerDependencyInstaller."""

    def test_bind_mounts(self, tmp_path: Path) -> None:
        """Test bind_mounts."""
        requirements_txt = tmp_path / "requirements.txt"
        project = Mock(
            cache_dir=False,
            dependency_directory="dependency_directory",
            project_root="project_root",
            requirements_txt=requirements_txt,
        )
        obj = PythonDockerDependencyInstaller(project, client=Mock())
        assert obj.bind_mounts == [
            Mount(target="/var/task/lambda", source="dependency_directory", type="bind"),
            Mount(target="/var/task/project", source="project_root", type="bind"),
            Mount(
                target=f"/var/task/{requirements_txt.name}",
                source=str(requirements_txt),
                type="bind",
            ),
        ]

    def test_environment_variables(self) -> None:
        """Test environment_variables."""
        expected = {"DOCKER_SETTINGS": "something", "PIP_SETTINGS": "foobar"}
        env_vars = {"FOO": "BAR", "PATH": "/dev/null", **expected}
        ctx = Mock(env=Mock(vars=env_vars))
        obj = PythonDockerDependencyInstaller(Mock(ctx=ctx), client=Mock())
        assert obj.environment_variables == expected

    @pytest.mark.parametrize(
        "pipenv, poetry", [(False, False), (False, True), (True, False), (True, True)]
    )
    def test_install_commands(
        self, mocker: MockerFixture, pipenv: bool, poetry: bool, tmp_path: Path
    ) -> None:
        """Test install_commands."""
        args = Mock(extend_pip_args=["--foo", "bar"], use_cache=True)
        mock_generate_install_command = Mock(return_value=["cmd"])
        mock_join = mocker.patch(f"{MODULE}.shlex_join", return_value="success")
        requirements_txt = tmp_path / "requirements.txt"
        project = Mock(
            args=args,
            cache_dir="cache_dir",
            pip=Mock(generate_install_command=mock_generate_install_command),
            pipenv=pipenv,
            poetry=poetry,
            requirements_txt=requirements_txt,
        )
        obj = PythonDockerDependencyInstaller(project, client=Mock())
        assert obj.install_commands == [mock_join.return_value]
        mock_generate_install_command.assert_called_once_with(
            cache_dir=obj.CACHE_DIR,
            no_deps=bool(pipenv or poetry),
            no_cache_dir=False,
            requirements=f"/var/task/{requirements_txt.name}",
            target=PythonDockerDependencyInstaller.DEPENDENCY_DIR,
        )
        mock_join.assert_called_once_with(
            mock_generate_install_command.return_value + args.extend_pip_args
        )

    def test_install_commands_no_requirements(self) -> None:
        """Test install_commands no requirements."""
        result = PythonDockerDependencyInstaller(
            Mock(requirements_txt=None), client=Mock()
        ).install_commands
        assert not result and isinstance(result, list)

    def test_python_version(self, mocker: MockerFixture) -> None:
        """Test python_version."""
        version = "3.10.0"
        mock_run_command = mocker.patch.object(
            PythonDockerDependencyInstaller,
            "run_command",
            return_value=[f"Python {version}"],
        )
        mock_version_cls = mocker.patch(f"{MODULE}.Version", return_value="success")
        obj = PythonDockerDependencyInstaller(Mock(), client=Mock())
        assert obj.python_version == mock_version_cls.return_value
        mock_run_command.assert_called_once_with("python --version", level=logging.DEBUG)
        mock_version_cls.assert_called_once_with(version)

    def test_python_version_not_found(self, mocker: MockerFixture) -> None:
        """Test python_version not found."""
        mock_run_command = mocker.patch.object(
            PythonDockerDependencyInstaller,
            "run_command",
            return_value=[""],
        )
        mock_version_cls = mocker.patch(f"{MODULE}.Version")
        obj = PythonDockerDependencyInstaller(Mock(), client=Mock())
        assert not obj.python_version
        mock_run_command.assert_called_once_with("python --version", level=logging.DEBUG)
        mock_version_cls.assert_not_called()

    @pytest.mark.parametrize(
        "version, expected",
        [
            (Version("3.11.0"), "python3.11"),
            (Version("3.10.0"), "python3.10"),
            (Version("3.9.7"), "python3.9"),
            (Version("3.8.4"), "python3.8"),
            (None, None),
        ],
    )
    def test_runtime(
        self, expected: Optional[str], mocker: MockerFixture, version: Optional[Version]
    ) -> None:
        """Test runtime."""
        mocker.patch.object(PythonDockerDependencyInstaller, "python_version", version)
        assert PythonDockerDependencyInstaller(Mock(), client=Mock()).runtime == expected
