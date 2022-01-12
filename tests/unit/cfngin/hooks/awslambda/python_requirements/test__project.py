"""Test runway.cfngin.hooks.awslambda.python_requirements._project."""
# pylint: disable=no-self-use
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List, Sequence

import pytest
from mock import Mock, call

from runway.cfngin.hooks.awslambda.exceptions import RuntimeMismatchError
from runway.cfngin.hooks.awslambda.python_requirements import PythonProject
from runway.dependency_managers import (
    Pip,
    Pipenv,
    PipenvNotFoundError,
    PipInstallFailedError,
    Poetry,
    PoetryNotFoundError,
)

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import LogCaptureFixture
    from pytest_mock import MockerFixture


MODULE = "runway.cfngin.hooks.awslambda.python_requirements._project"


class TestPythonProject:
    """Test PythonProject."""

    @pytest.mark.parametrize(
        "file_exists, pipenv_value, poetry_value",
        [
            (False, False, False),
            (False, False, True),
            (False, True, True),
            (False, True, False),
            (True, False, False),
            (True, False, True),
            (True, True, True),
        ],
    )
    def test_cleanup(
        self,
        file_exists: bool,
        mocker: MockerFixture,
        pipenv_value: bool,
        poetry_value: bool,
    ) -> None:
        """Test cleanup."""
        build_directory = mocker.patch.object(
            PythonProject,
            "build_directory",
            Mock(name="build_directory", iterdir=Mock(return_value=iter([]))),
        )
        dependency_directory = mocker.patch.object(
            PythonProject, "dependency_directory", "dependency_directory"
        )
        mock_rmtree = mocker.patch("shutil.rmtree")
        tmp_requirements_txt = mocker.patch.object(
            PythonProject,
            "tmp_requirements_txt",
            Mock(exists=Mock(return_value=file_exists)),
        )
        mocker.patch.object(PythonProject, "pipenv", pipenv_value)
        mocker.patch.object(PythonProject, "poetry", poetry_value)

        assert not PythonProject(Mock(), Mock()).cleanup()
        if pipenv_value or poetry_value:
            tmp_requirements_txt.exists.assert_called_once_with()
        else:
            tmp_requirements_txt.exists.assert_not_called()
        if (
            max([sum([file_exists, pipenv_value]), sum([file_exists, poetry_value])])
            == 2
        ):
            tmp_requirements_txt.unlink.assert_called_once_with()
        else:
            tmp_requirements_txt.unlink.assert_not_called()
        build_directory.iterdir.assert_called_once_with()
        mock_rmtree.assert_has_calls(
            [  # type: ignore
                call(dependency_directory, ignore_errors=True),
                call(build_directory, ignore_errors=True),
            ]
        )

    def test_cleanup_build_directory_not_empty(self, mocker: MockerFixture) -> None:
        """Test cleanup build_directory not empty."""
        build_directory = mocker.patch.object(
            PythonProject,
            "build_directory",
            Mock(name="build_directory", iterdir=Mock(return_value=iter(["foobar"]))),
        )
        dependency_directory = mocker.patch.object(
            PythonProject, "dependency_directory", "dependency_directory"
        )
        mock_rmtree = mocker.patch("shutil.rmtree")
        mocker.patch.object(
            PythonProject,
            "tmp_requirements_txt",
            Mock(exists=Mock(return_value=False)),
        )
        mocker.patch.object(PythonProject, "pipenv", None)
        mocker.patch.object(PythonProject, "poetry", None)

        assert not PythonProject(Mock(), Mock()).cleanup()
        build_directory.iterdir.assert_called_once_with()
        mock_rmtree.assert_called_once_with(dependency_directory, ignore_errors=True)

    def test_docker(self, mocker: MockerFixture) -> None:
        """Test docker."""
        from_project = mocker.patch(
            f"{MODULE}.PythonDockerDependencyInstaller.from_project",
            return_value="success",
        )
        obj = PythonProject(Mock(), Mock())
        assert obj.docker == from_project.return_value
        from_project.assert_called_once_with(obj)

    @pytest.mark.parametrize(
        "pipenv, poetry", [(False, False), (False, True), (True, False), (True, True)]
    )
    def test_install_dependencies(
        self, mocker: MockerFixture, pipenv: bool, poetry: bool
    ) -> None:
        """Test install_dependencies."""
        args = Mock(cache_dir="foo", extend_pip_args=["--foo", "bar"], use_cache=True)
        mocker.patch.object(PythonProject, "pipenv", pipenv)
        mocker.patch.object(PythonProject, "poetry", poetry)
        dependency_directory = mocker.patch.object(
            PythonProject, "dependency_directory", "dependency_directory"
        )
        mock_pip = mocker.patch.object(PythonProject, "pip", Mock())
        requirements_txt = mocker.patch.object(
            PythonProject, "requirements_txt", "requirements_txt"
        )
        assert not PythonProject(args, Mock()).install_dependencies()
        mock_pip.install.assert_called_once_with(
            cache_dir="foo",
            extend_args=args.extend_pip_args,
            no_cache_dir=False,
            no_deps=bool(pipenv or poetry),
            requirements=requirements_txt,
            target=dependency_directory,
        )

    def test_install_dependencies_docker(self, mocker: MockerFixture) -> None:
        """Test install_dependencies using Docker."""
        mock_docker = mocker.patch.object(PythonProject, "docker")
        mock_pip = mocker.patch.object(PythonProject, "pip")
        mocker.patch.object(
            PythonProject, "dependency_directory", "dependency_directory"
        )
        mocker.patch.object(PythonProject, "requirements_txt", "requirements.txt")
        assert not PythonProject(Mock(), Mock()).install_dependencies()
        mock_docker.install.assert_called_once_with()
        mock_pip.install.assert_not_called()

    def test_install_dependencies_does_not_catch_errors(
        self, mocker: MockerFixture
    ) -> None:
        """Test install_dependencies does not catch errors."""
        mocker.patch.object(PythonProject, "pipenv", False)
        mocker.patch.object(PythonProject, "poetry", False)
        dependency_directory = mocker.patch.object(
            PythonProject, "dependency_directory", "dependency_directory"
        )
        mock_pip = mocker.patch.object(
            PythonProject, "pip", Mock(install=Mock(side_effect=PipInstallFailedError))
        )
        requirements_txt = mocker.patch.object(
            PythonProject, "requirements_txt", "requirements_txt"
        )
        with pytest.raises(PipInstallFailedError):
            assert not PythonProject(
                Mock(cache_dir="foo", extend_pip_args=None, use_cache=True), Mock()
            ).install_dependencies()
        mock_pip.install.assert_called_once_with(
            cache_dir="foo",
            extend_args=None,
            no_cache_dir=False,
            no_deps=False,
            requirements=requirements_txt,
            target=dependency_directory,
        )

    def test_install_dependencies_skip(
        self, caplog: LogCaptureFixture, mocker: MockerFixture
    ) -> None:
        """Test install_dependencies skip because no dependencies."""
        caplog.set_level(logging.INFO, logger=MODULE.replace("._", "."))
        mock_docker = mocker.patch.object(PythonProject, "docker")
        mock_pip = mocker.patch.object(PythonProject, "pip")
        mocker.patch.object(
            PythonProject, "dependency_directory", "dependency_directory"
        )
        mocker.patch.object(PythonProject, "requirements_txt", None)
        assert not PythonProject(Mock(), Mock()).install_dependencies()
        mock_docker.install.assert_not_called()
        mock_pip.install.assert_not_called()
        assert "skipped installing dependencies; none found" in caplog.messages

    @pytest.mark.parametrize(
        "project_type, expected_files",
        [
            ("pip", Pip.CONFIG_FILES),
            ("pipenv", Pipenv.CONFIG_FILES),
            ("pipenv", [Pipenv.CONFIG_FILES[1]]),
            ("poetry", Poetry.CONFIG_FILES),
            ("poetry", [Poetry.CONFIG_FILES[1]]),
        ],
    )
    def test_metadata_files(
        self,
        expected_files: Sequence[str],
        mocker: MockerFixture,
        project_type: str,
        tmp_path: Path,
    ) -> None:
        """Test metadata_files.

        expected_files can be a subset of <class>.CONFIG_FILES to ensure that
        return value only contains files that exist as these files are created.

        """
        expected = tuple(tmp_path / expected_file for expected_file in expected_files)
        for expected_file in expected:
            expected_file.touch()
        mocker.patch.object(PythonProject, "project_root", tmp_path)
        mocker.patch.object(PythonProject, "project_type", project_type)
        assert PythonProject(Mock(), Mock()).metadata_files == expected

    def test_pip(self, mocker: MockerFixture) -> None:
        """Test pip."""
        ctx = Mock()
        pip_class = mocker.patch(f"{MODULE}.Pip", return_value="Pip")
        project_root = mocker.patch.object(PythonProject, "project_root")
        assert PythonProject(Mock(), ctx).pip == pip_class.return_value
        pip_class.assert_called_once_with(ctx, project_root)

    def test_pipenv(self, mocker: MockerFixture) -> None:
        """Test pipenv."""
        ctx = Mock()
        pipenv_class = mocker.patch(
            f"{MODULE}.Pipenv",
            Mock(found_in_path=Mock(return_value=True), return_value="Pipenv"),
        )
        mocker.patch.object(PythonProject, "project_type", "pipenv")
        project_root = mocker.patch.object(PythonProject, "project_root")
        assert (
            PythonProject(Mock(use_poetry=True), ctx).pipenv
            == pipenv_class.return_value
        )
        pipenv_class.found_in_path.assert_called_once_with()
        pipenv_class.assert_called_once_with(ctx, project_root)

    def test_pipenv_not_in_path(self, mocker: MockerFixture) -> None:
        """Test pipenv not in path."""
        pipenv_class = mocker.patch(
            f"{MODULE}.Pipenv",
            Mock(found_in_path=Mock(return_value=False)),
        )
        mocker.patch.object(PythonProject, "project_type", "pipenv")
        mocker.patch.object(PythonProject, "project_root")
        with pytest.raises(PipenvNotFoundError):
            assert PythonProject(Mock(use_pipenv=True), Mock()).pipenv
        pipenv_class.found_in_path.assert_called_once_with()

    def test_pipenv_not_pipenv_project(self, mocker: MockerFixture) -> None:
        """Test pipenv project is not a pipenv project."""
        mocker.patch.object(PythonProject, "project_type", "poetry")
        mocker.patch.object(PythonProject, "project_root")
        assert not PythonProject(Mock(use_pipenv=True), Mock()).pipenv

    def test_poetry(self, mocker: MockerFixture) -> None:
        """Test poetry."""
        ctx = Mock()
        poetry_class = mocker.patch(
            f"{MODULE}.Poetry",
            Mock(found_in_path=Mock(return_value=True), return_value="Poetry"),
        )
        mocker.patch.object(PythonProject, "project_type", "poetry")
        project_root = mocker.patch.object(PythonProject, "project_root")
        assert (
            PythonProject(Mock(use_poetry=True), ctx).poetry
            == poetry_class.return_value
        )
        poetry_class.found_in_path.assert_called_once_with()
        poetry_class.assert_called_once_with(ctx, project_root)

    def test_poetry_not_in_path(self, mocker: MockerFixture) -> None:
        """Test poetry not in path."""
        poetry_class = mocker.patch(
            f"{MODULE}.Poetry",
            Mock(found_in_path=Mock(return_value=False)),
        )
        mocker.patch.object(PythonProject, "project_type", "poetry")
        mocker.patch.object(PythonProject, "project_root")
        with pytest.raises(PoetryNotFoundError):
            assert PythonProject(Mock(use_poetry=True), Mock()).poetry
        poetry_class.found_in_path.assert_called_once_with()

    def test_poetry_not_poetry_project(self, mocker: MockerFixture) -> None:
        """Test poetry project is not a poetry project."""
        mocker.patch.object(PythonProject, "project_type", "pipenv")
        mocker.patch.object(PythonProject, "project_root")
        assert not PythonProject(Mock(use_poetry=True), Mock()).poetry

    @pytest.mark.parametrize(
        "pipenv_project, poetry_project, use_pipenv, use_poetry, expected",
        [
            (False, False, False, False, "pip"),
            (False, False, False, True, "pip"),
            (False, False, True, True, "pip"),
            (False, True, False, False, "pip"),
            (False, True, True, False, "pip"),
            (True, False, False, False, "pip"),
            (True, False, False, True, "pip"),
            (True, True, False, False, "pip"),
            (False, True, False, True, "poetry"),
            (False, True, True, True, "poetry"),
            (True, True, True, True, "poetry"),
            (True, True, True, False, "pipenv"),
            (True, False, True, False, "pipenv"),
            (True, False, True, True, "pipenv"),
        ],
    )
    def test_project_type(
        self,
        caplog: LogCaptureFixture,
        expected: str,
        mocker: MockerFixture,
        pipenv_project: bool,
        poetry_project: bool,
        tmp_path: Path,
        use_pipenv: bool,
        use_poetry: bool,
    ) -> None:
        """Test project_type."""
        caplog.set_level(logging.WARNING)
        mocker.patch.object(PythonProject, "project_root", tmp_path)
        mock_pipenv_dir_is_project = mocker.patch(
            f"{MODULE}.Pipenv.dir_is_project", return_value=pipenv_project
        )
        mock_poetry_dir_is_project = mocker.patch(
            f"{MODULE}.Poetry.dir_is_project", return_value=poetry_project
        )
        assert (
            PythonProject(
                Mock(use_pipenv=use_pipenv, use_poetry=use_poetry),
                Mock(),
            ).project_type
            == expected
        )
        mock_poetry_dir_is_project.assert_called_once_with(tmp_path)
        if poetry_project:
            if use_poetry:
                mock_pipenv_dir_is_project.assert_not_called()
            else:
                assert (
                    "poetry project detected but use of poetry is explicitly disabled"
                    in caplog.messages
                )
        else:
            mock_pipenv_dir_is_project.assert_called_once_with(tmp_path)
        if (pipenv_project and not use_pipenv) and sum(
            [poetry_project, use_poetry]
        ) != 2:
            assert (
                "pipenv project detected but use of pipenv is explicitly disabled"
                in caplog.messages
            )

    def test_requirements_txt(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test requirements_txt."""
        expected = tmp_path / "requirements.txt"
        expected.touch()
        mock_dir_is_project = mocker.patch(
            f"{MODULE}.Pip.dir_is_project", return_value=True
        )
        mocker.patch.object(PythonProject, "pipenv", None)
        mocker.patch.object(PythonProject, "poetry", None)
        mocker.patch.object(PythonProject, "project_root", tmp_path)
        assert PythonProject(Mock(), Mock()).requirements_txt == expected
        mock_dir_is_project.assert_called_once_with(tmp_path, file_name=expected.name)

    def test_requirements_txt_none(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test requirements_txt is None."""
        mock_dir_is_project = mocker.patch(
            f"{MODULE}.Pip.dir_is_project", return_value=False
        )
        mocker.patch.object(PythonProject, "pipenv", None)
        mocker.patch.object(PythonProject, "poetry", None)
        mocker.patch.object(PythonProject, "project_root", tmp_path)
        assert not PythonProject(Mock(), Mock()).requirements_txt
        mock_dir_is_project.assert_called_once_with(
            tmp_path, file_name="requirements.txt"
        )

    def test_requirements_txt_pipenv(self, mocker: MockerFixture) -> None:
        """Test requirements_txt."""
        expected = "foo.txt"
        pipenv = mocker.patch.object(
            PythonProject, "pipenv", Mock(export=Mock(return_value=expected))
        )
        tmp_requirements_txt = mocker.patch.object(
            PythonProject, "tmp_requirements_txt", "tmp_requirements_txt"
        )
        mocker.patch.object(PythonProject, "poetry", None)
        mocker.patch.object(PythonProject, "project_root")
        assert PythonProject(Mock(), Mock()).requirements_txt == expected
        pipenv.export.assert_called_once_with(output=tmp_requirements_txt)

    def test_requirements_txt_poetry(self, mocker: MockerFixture) -> None:
        """Test requirements_txt."""
        expected = "foo.txt"
        poetry = mocker.patch.object(
            PythonProject, "poetry", Mock(export=Mock(return_value=expected))
        )
        tmp_requirements_txt = mocker.patch.object(
            PythonProject, "tmp_requirements_txt", "tmp_requirements_txt"
        )
        mocker.patch.object(PythonProject, "pipenv", None)
        mocker.patch.object(PythonProject, "project_root")
        assert PythonProject(Mock(), Mock()).requirements_txt == expected
        poetry.export.assert_called_once_with(output=tmp_requirements_txt)

    def test_runtime(self, mocker: MockerFixture) -> None:
        """Test runtime from docker."""
        docker = mocker.patch.object(PythonProject, "docker", Mock(runtime="foo"))
        assert PythonProject(Mock(runtime=None), Mock()).runtime == docker.runtime

    def test_runtime_pip(self, mocker: MockerFixture) -> None:
        """Test runtime from pip."""
        mocker.patch.object(PythonProject, "docker", None)
        mocker.patch.object(
            PythonProject, "pip", Mock(python_version=Mock(major="3", minor="9"))
        )
        assert PythonProject(Mock(runtime=None), Mock()).runtime == "python3.9"

    def test_runtime_raise_runtime_mismatch_error_docker(
        self, mocker: MockerFixture
    ) -> None:
        """Test runtime raise RuntimeMismatchError."""
        args = Mock(runtime="bar")
        docker = mocker.patch.object(PythonProject, "docker", Mock(runtime="foo"))
        with pytest.raises(RuntimeMismatchError) as excinfo:
            assert not PythonProject(args, Mock()).runtime
        assert excinfo.value.detected_runtime == docker.runtime
        assert excinfo.value.expected_runtime == args.runtime

    def test_runtime_raise_runtime_mismatch_error_pip(
        self, mocker: MockerFixture
    ) -> None:
        """Test runtime raise RuntimeMismatchError."""
        args = Mock(runtime="bar")
        mocker.patch.object(PythonProject, "docker", None)
        mocker.patch.object(
            PythonProject, "pip", Mock(python_version=Mock(major="3", minor="9"))
        )
        with pytest.raises(RuntimeMismatchError) as excinfo:
            assert not PythonProject(args, Mock()).runtime
        assert excinfo.value.detected_runtime == "python3.9"
        assert excinfo.value.expected_runtime == args.runtime

    @pytest.mark.parametrize(
        "use_pipenv, use_poetry, update_expected",
        [
            (False, False, []),
            (False, True, [*Poetry.CONFIG_FILES]),
            (True, False, [*Pipenv.CONFIG_FILES]),
            (True, True, [*Poetry.CONFIG_FILES, *Pipenv.CONFIG_FILES]),
        ],
    )
    def test_supported_metadata_files(
        self, update_expected: List[str], use_pipenv: bool, use_poetry: bool
    ) -> None:
        """Test supported_metadata_files."""
        expected = {*Pip.CONFIG_FILES}
        if update_expected:
            expected.update(update_expected)
        assert (
            PythonProject(
                Mock(use_pipenv=use_pipenv, use_poetry=use_poetry), Mock()
            ).supported_metadata_files
            == expected
        )

    def test_tmp_requirements_txt(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test tmp_requirements_txt."""
        mocker.patch(f"{MODULE}.BASE_WORK_DIR", tmp_path)
        source_code = mocker.patch.object(
            PythonProject, "source_code", Mock(md5_hash="hash")
        )
        assert (
            PythonProject(Mock(), Mock()).tmp_requirements_txt
            == tmp_path / f"{source_code.md5_hash}.requirements.txt"
        )
