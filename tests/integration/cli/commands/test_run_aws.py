"""Test ``runway run-aws`` command."""
from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from click.testing import CliRunner

from runway._cli import cli

if sys.version_info < (3, 8):
    # importlib.metadata is standard lib for python>=3.8, use backport
    from importlib_metadata import version  # pylint: disable=E
else:
    from importlib.metadata import version  # pylint: disable=E

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch


def test_run_aws_head_bucket(monkeypatch: MonkeyPatch) -> None:
    """Test ``runway run-aws s3api head-bucket``."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("DEBUG", "0")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "run-aws",
            "s3api",
            "head-bucket",
            "--bucket",
            "example-bucket",
            "--region",
            "us-east-1",
        ],
    )
    assert result.exit_code != 0
    # exact error could differ
    assert "when calling the HeadBucket operation:" in result.output


def test_run_aws_version() -> None:
    """Test ``runway run-aws --version``."""
    runner = CliRunner()
    result = runner.invoke(cli, ["run-aws", "--version"])
    assert result.exit_code == 0
    assert version("awscli") in result.output


def test_run_aws_version_separator() -> None:
    """Test ``runway run-aws -- --version``."""
    runner = CliRunner()
    result = runner.invoke(cli, ["run-aws", "--", "--version"])
    assert result.exit_code == 0
    assert version("awscli") in result.output
