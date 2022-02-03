"""Tests for runway.cfngin.hooks.command."""
# pylint: disable=no-self-use
# pyright: basic
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from runway.cfngin.exceptions import ImproperlyConfigured
from runway.cfngin.hooks.command import run_command

if TYPE_CHECKING:
    from pytest_subprocess import FakeProcess


def test_run_command(fake_process: FakeProcess) -> None:
    """Test run_command."""
    fake_process.register_subprocess(["foo"], returncode=0)
    assert run_command(command=["foo"]) == {
        "returncode": 0,
        "stderr": None,
        "stdout": None,
    }


def test_run_command_capture(fake_process: FakeProcess) -> None:
    """Test run_command with ``capture``."""
    fake_process.register_subprocess(
        ["foo"], returncode=0, stderr="bar", stdout="foobar"
    )
    assert run_command(command=["foo"], capture=True) == {
        "returncode": 0,
        "stderr": b"bar",  # for some reason, pytest-subprocess returns these as bytes
        "stdout": b"foobar",
    }


def test_run_command_env(fake_process: FakeProcess) -> None:
    """Test run_command with ``env``."""
    fake_process.register_subprocess(["foo"], returncode=0)
    assert run_command(command=["foo"], env={"TEST": "bar"}) == {
        "returncode": 0,
        "stderr": None,
        "stdout": None,
    }


def test_run_command_fail(fake_process: FakeProcess) -> None:
    """Test run_command non-zero exit code."""
    fake_process.register_subprocess(["foo"], returncode=1)
    assert not run_command(command=["foo"])


def test_run_command_interactive(fake_process: FakeProcess) -> None:
    """Test run_command with ``interactive``."""
    fake_process.register_subprocess(["foo"], returncode=0)
    assert run_command(command=["foo"], interactive=True) == {
        "returncode": 0,
        "stderr": None,
        "stdout": None,
    }


def test_run_command_ignore_status(fake_process: FakeProcess) -> None:
    """Test run_command with ``ignore_status``."""
    fake_process.register_subprocess(["foo"], returncode=1)
    assert run_command(command=["foo"], ignore_status=True) == {
        "returncode": 1,
        "stderr": None,
        "stdout": None,
    }


def test_run_command_quiet(fake_process: FakeProcess) -> None:
    """Test run_command with ``quiet``."""
    fake_process.register_subprocess(["foo"], returncode=0, stderr="", stdout="")
    assert run_command(command=["foo"], quiet=True) == {
        "returncode": 0,
        "stderr": None,
        "stdout": None,
    }


def test_run_command_raise_improperly_configured() -> None:
    """Test run_command raise ``ImproperlyConfigured``."""
    with pytest.raises(ImproperlyConfigured):
        run_command(command=["foo"], capture=True, quiet=True)


def test_run_command_stdin(fake_process: FakeProcess) -> None:
    """Test run_command with ``stdin``."""
    fake_process.register_subprocess(["foo"], returncode=0)
    assert run_command(command=["foo"], stdin="bar") == {
        "returncode": 0,
        "stderr": None,
        "stdout": None,
    }
