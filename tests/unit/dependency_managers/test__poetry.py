"""Test runway.dependency_managers._poetry."""
# pylint: disable=no-self-use
from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING, Any, Dict

import pytest
import tomli_w
from mock import Mock

from runway.dependency_managers import Poetry, PoetryExportFailedError

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

MODULE = "runway.dependency_managers._poetry"


class TestPoetry:
    """Test Poetry."""

    def test_config_files(self) -> None:
        """Test CONFIG_FILES."""
        assert Poetry.CONFIG_FILES == ("poetry.lock", "pyproject.toml")

    @pytest.mark.parametrize(
        "build_system, expected",
        [
            (
                {
                    "build-backend": "poetry.core.masonry.api",
                    "requires": ["poetry-core>=1.0.0"],
                },
                True,
            ),
            ({"requires": ["poetry-core>=1.0.0"]}, True),
            ({"build-backend": "poetry.core.masonry.api"}, False),
            ({}, False),
        ],
    )
    def test_dir_is_project(
        self, build_system: Dict[str, Any], expected: bool, tmp_path: Path
    ) -> None:
        """Test dir_is_project."""
        pyproject_contents = {"build-system": build_system}
        pyproject_path = tmp_path / "pyproject.toml"
        pyproject_path.write_text(tomli_w.dumps(pyproject_contents))
        assert Poetry.dir_is_project(tmp_path) is expected

    def test_dir_is_project_file_not_found(self, tmp_path: Path) -> None:
        """Test dir_is_project for pyproject.toml not in directory."""
        assert not Poetry.dir_is_project(tmp_path)

    @pytest.mark.parametrize(
        "export_kwargs",
        [
            {},
            {
                "dev": True,
                "extras": ["foo"],
                "output_format": "pipenv",
                "with_credentials": False,
                "without_hashes": False,
            },
        ],
    )
    def test_export(
        self,
        export_kwargs: Dict[str, Any],
        mocker: MockerFixture,
        tmp_path: Path,
    ) -> None:
        """Test export."""
        expected = tmp_path / "expected" / "test.requirements.txt"
        mock_generate_command = mocker.patch.object(
            Poetry, "generate_command", return_value="generate_command"
        )
        mock_run_command = mocker.patch.object(
            Poetry, "_run_command", return_value="_run_command"
        )
        (tmp_path / "test.requirements.txt").touch()  # created by _run_command

        obj = Poetry(Mock(), tmp_path)
        assert obj.export(output=expected, **export_kwargs) == expected
        assert expected.is_file()
        export_kwargs.update({"output": expected.name})
        export_kwargs.update(
            {"format": export_kwargs.pop("output_format", "requirements.txt")}
        )
        export_kwargs.setdefault("dev", False)
        export_kwargs.setdefault("extras", None)
        export_kwargs.setdefault("with_credentials", True)
        export_kwargs.setdefault("without_hashes", True)
        mock_generate_command.assert_called_once_with("export", **export_kwargs)
        mock_run_command.assert_called_once_with(mock_generate_command.return_value)

    def test_export_raise_from_called_process_error(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
    ) -> None:
        """Test export raise PoetryExportFailedError from CalledProcessError."""
        output = tmp_path / "expected" / "test.requirements.txt"
        mock_generate_command = mocker.patch.object(
            Poetry, "generate_command", return_value="generate_command"
        )
        mocker.patch.object(
            Poetry,
            "_run_command",
            side_effect=subprocess.CalledProcessError(
                returncode=1,
                cmd=mock_generate_command.return_value,
                output="output",
                stderr="stderr",
            ),
        )

        with pytest.raises(PoetryExportFailedError) as excinfo:
            assert Poetry(Mock(), tmp_path).export(output=output)
        assert (
            excinfo.value.message
            == "poetry export failed with the following output:\nstderr"
        )

    def test_export_raise_when_output_does_not_exist(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
    ) -> None:
        """Test export raise PoetryExportFailedError from CalledProcessError."""
        output = tmp_path / "expected" / "test.requirements.txt"
        mocker.patch.object(Poetry, "generate_command", return_value="generate_command")
        mock_run_command = mocker.patch.object(
            Poetry, "_run_command", return_value="_run_command"
        )

        with pytest.raises(PoetryExportFailedError) as excinfo:
            assert Poetry(Mock(), tmp_path).export(output=output)
        assert (
            excinfo.value.message
            == f"poetry export failed with the following output:\n{mock_run_command.return_value}"
        )

    @pytest.mark.parametrize(
        "cmd_output, expected",
        [("Poetry version 1.1.11", "1.1.11"), ("unexpected output", "0.0.0")],
    )
    def test_version(
        self, cmd_output: str, expected: str, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """Test version."""
        mock_run_command = mocker.patch.object(
            Poetry, "_run_command", return_value=cmd_output
        )
        version_cls = mocker.patch(f"{MODULE}.Version", return_value="success")
        assert Poetry(Mock(), tmp_path).version == version_cls.return_value
        mock_run_command.assert_called_once_with([Poetry.EXECUTABLE, "--version"])
        version_cls.assert_called_once_with(expected)
