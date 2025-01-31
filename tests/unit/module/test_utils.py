"""Test runway.module.utils."""

from __future__ import annotations

from subprocess import CalledProcessError
from typing import TYPE_CHECKING, Any

import pytest

from runway.module.utils import (
    NPM_BIN,
    NPX_BIN,
    format_npm_command_for_logging,
    generate_node_command,
    run_module_command,
    use_npm_ci,
)

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture
    from pytest_subprocess import FakeProcess

MODULE = "runway.module.utils"


@pytest.mark.parametrize(
    "command, expected",
    [
        (["npx.cmd", "-c", "hello-world"], "npx.cmd -c hello-world"),
        (["npx", "-c", "hello-world"], "npx -c hello-world"),
        (["npm.cmd", "hello-world"], "npm.cmd hello-world"),
        (["npm", "hello-world"], "npm hello-world"),
    ],
)
def test_format_npm_command_for_logging_darwin(
    command: list[str],
    expected: str,
    platform_darwin: None,  # noqa: ARG001
) -> None:
    """Test format_npm_command_for_logging on Darwin/macOS."""
    assert format_npm_command_for_logging(command) == expected


@pytest.mark.parametrize(
    "command, expected",
    [
        (["npx.cmd", "-c", "hello-world"], 'npx.cmd -c "hello-world"'),
        (["npx", "-c", "hello-world"], "npx -c hello-world"),
        (["npm.cmd", "hello-world"], "npm.cmd hello-world"),
        (["npm", "hello-world"], "npm hello-world"),
    ],
)
def test_format_npm_command_for_logging_windows(
    command: list[str],
    expected: str,
    platform_windows: None,  # noqa: ARG001
) -> None:
    """Test format_npm_command_for_logging on windows."""
    assert format_npm_command_for_logging(command) == expected


@pytest.mark.parametrize(
    "command, opts", [("test", []), ("test", ["arg1"]), ("test", ["arg1", "arg2"])]
)
def test_generate_node_command(
    command: str, mocker: MockerFixture, opts: list[str], tmp_path: Path
) -> None:
    """Test generate_node_command."""
    mock_which = mocker.patch(f"{MODULE}.which", return_value=False)
    assert generate_node_command(command, opts, tmp_path) == [
        str(tmp_path / "node_modules" / ".bin" / command),
        *opts,
    ]
    mock_which.assert_called_once_with(NPX_BIN)


@pytest.mark.parametrize(
    "command, opts, expected",
    [
        ("test", [], [NPX_BIN, "-c", "test"]),
        ("test", ["arg1"], [NPX_BIN, "-c", "test arg1"]),
        ("test", ["arg1", "arg2"], [NPX_BIN, "-c", "test arg1 arg2"]),
    ],
)
def test_generate_node_command_npx(
    command: str,
    expected: list[str],
    mocker: MockerFixture,
    opts: list[str],
    tmp_path: Path,
) -> None:
    """Test generate_node_command."""
    mock_which = mocker.patch(f"{MODULE}.which", return_value=True)
    assert generate_node_command(command, opts, tmp_path) == expected
    mock_which.assert_called_once_with(NPX_BIN)


def test_generate_node_command_npx_package(mocker: MockerFixture, tmp_path: Path) -> None:
    """Test generate_node_command."""
    mock_which = mocker.patch(f"{MODULE}.which", return_value=True)
    assert generate_node_command(
        command="cdk",
        command_opts=["--context", "key=val"],
        package="aws-cdk",
        path=tmp_path,
    ) == [NPX_BIN, "--package", "aws-cdk", "cdk", "--context", "key=val"]
    mock_which.assert_called_once_with(NPX_BIN)


def test_run_module_command_called_process_error(fake_process: FakeProcess) -> None:
    """Test run_module_command raise CalledProcessError."""
    cmd = ["test"]
    fake_process.register_subprocess(cmd, returncode=1)  # type: ignore
    with pytest.raises(CalledProcessError):
        run_module_command(cmd, {}, exit_on_error=False)
    assert fake_process.call_count(cmd) == 1  # type: ignore


def test_run_module_command_exit_on_error_system_exit(
    fake_process: FakeProcess,
) -> None:
    """Test run_module_command raise SystemExit."""
    cmd = ["test"]
    fake_process.register_subprocess(cmd, returncode=1)  # type: ignore
    with pytest.raises(SystemExit):
        run_module_command(cmd, {})
    assert fake_process.call_count(cmd) == 1  # type: ignore


def test_run_module_command_exit_on_error(fake_process: FakeProcess) -> None:
    """Test run_module_command exit_on_error no error."""
    cmd = ["test"]
    fake_process.register_subprocess(cmd, returncode=0)  # type: ignore
    assert not run_module_command(cmd, {})
    assert fake_process.call_count(cmd) == 1  # type: ignore


def test_run_module_command(fake_process: FakeProcess) -> None:
    """Test run_module_command."""
    cmd = ["test"]
    fake_process.register_subprocess(cmd, returncode=0)  # type: ignore
    assert not run_module_command(cmd, {}, exit_on_error=False)
    assert fake_process.call_count(cmd) == 1  # type: ignore


@pytest.mark.parametrize(
    "has_lock, has_shrinkwrap, exit_code, expected",
    [
        (False, False, 0, False),
        (False, False, 1, False),
        (True, False, 1, False),
        (False, True, 1, False),
        (True, True, 1, False),
        (True, False, 0, True),
        (False, True, 0, True),
        (True, True, 0, True),
    ],
)
def test_use_npm_ci(
    exit_code: int,
    expected: bool,
    fake_process: FakeProcess,
    has_lock: bool,
    has_shrinkwrap: bool,
    tmp_path: Path,
) -> None:
    """Test use_npm_ci."""
    if has_lock:
        (tmp_path / "package-lock.json").touch()
    if has_shrinkwrap:
        (tmp_path / "package-lock.json").touch()
    cmd: list[Any] = [NPM_BIN, "ci", "-h"]
    fake_process.register_subprocess(cmd, returncode=exit_code)

    assert use_npm_ci(tmp_path) is expected
    if has_lock or has_shrinkwrap:
        assert fake_process.call_count(cmd) == 1
    else:
        assert fake_process.call_count(cmd) == 0
