"""Test runway.dependency_manager._pipenv."""

from __future__ import annotations

import logging
import subprocess
from typing import TYPE_CHECKING, Any
from unittest.mock import Mock, call

import pytest

from runway.dependency_managers import Pipenv, PipenvExportFailedError

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

    from ..factories import MockCfnginContext

MODULE = "runway.dependency_managers._pipenv"


class TestPipenv:
    """Test pipenv."""

    def test_config_files(self) -> None:
        """Test CONFIG_FILES."""
        assert Pipenv.CONFIG_FILES == ("Pipfile", "Pipfile.lock")

    @pytest.mark.parametrize(
        "lock_exists, pipfile_exists",
        [(False, False), (False, True), (True, True), (True, False)],
    )
    def test_dir_is_project(
        self,
        caplog: pytest.LogCaptureFixture,
        lock_exists: bool,
        pipfile_exists: bool,
        tmp_path: Path,
    ) -> None:
        """Test dir_is_project."""
        caplog.set_level(logging.WARNING)
        if lock_exists:
            (tmp_path / "Pipfile.lock").touch()
        if pipfile_exists:
            (tmp_path / "Pipfile").touch()
            assert Pipenv.dir_is_project(tmp_path)
            if not lock_exists:
                assert "Pipfile.lock not found" in caplog.messages
        else:
            assert not Pipenv.dir_is_project(tmp_path)

    @pytest.mark.parametrize(
        "export_kwargs",
        [
            {},
            {
                "dev": True,
            },
        ],
    )
    def test_export(
        self,
        export_kwargs: dict[str, Any],
        cfngin_context: MockCfnginContext,
        mocker: MockerFixture,
        tmp_path: Path,
    ) -> None:
        """Test export."""
        expected = tmp_path / "expected" / "test.requirements.txt"
        mock_generate_command = mocker.patch.object(
            Pipenv, "generate_command", side_effect=["lock", "requirements"]
        )
        mock_run_command = mocker.patch.object(Pipenv, "_run_command", return_value="_run_command")
        obj = Pipenv(cfngin_context, tmp_path)
        assert obj.export(output=expected, **export_kwargs) == expected
        assert expected.is_file()
        export_kwargs.setdefault("dev", False)
        mock_generate_command.assert_has_calls(
            [call("lock"), call("requirements", **export_kwargs)]
        )
        cfngin_context.env.vars["PIPENV_IGNORE_VIRTUALENVS"] = "1"
        mock_run_command.assert_has_calls(
            [
                call("lock", env=cfngin_context.env.vars),
                call("requirements", env=cfngin_context.env.vars, suppress_output=True),
            ]
        )

    def test_export_raise_from_called_process_error(
        self,
        cfngin_context: MockCfnginContext,
        mocker: MockerFixture,
        tmp_path: Path,
    ) -> None:
        """Test export raise PoetryExportFailedError from CalledProcessError."""
        output = tmp_path / "expected" / "test.requirements.txt"
        mocker.patch.object(Pipenv, "generate_command", side_effect=["lock", "requirements"])
        mock_run_command = mocker.patch.object(
            Pipenv,
            "_run_command",
            side_effect=[
                None,
                subprocess.CalledProcessError(
                    returncode=1,
                    cmd="pipenv requirements",
                ),
            ],
        )

        with pytest.raises(PipenvExportFailedError):
            assert Pipenv(cfngin_context, tmp_path).export(output=output)
        cfngin_context.env.vars["PIPENV_IGNORE_VIRTUALENVS"] = "1"
        mock_run_command.assert_has_calls(
            [
                call("lock", env=cfngin_context.env.vars),
                call("requirements", env=cfngin_context.env.vars, suppress_output=True),
            ]
        )

    @pytest.mark.parametrize(
        "cmd_output, expected",
        [("pipenv, version 2018.11.26", "2018.11.26"), ("unexpected output", "0.0.0")],
    )
    def test_version(
        self, cmd_output: str, expected: str, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """Test version."""
        mock_run_command = mocker.patch.object(Pipenv, "_run_command", return_value=cmd_output)
        version_cls = mocker.patch(f"{MODULE}.Version", return_value="success")
        assert Pipenv(Mock(), tmp_path).version == version_cls.return_value
        mock_run_command.assert_called_once_with([Pipenv.EXECUTABLE, "--version"])
        version_cls.assert_called_once_with(expected)
