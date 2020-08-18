"""Test ``runway run-aws`` command."""
import sys

from click.testing import CliRunner

from runway._cli import cli

if sys.version_info < (3, 8):
    # importlib.metadata is standard lib for python>=3.8, use backport
    from importlib_metadata import version
else:
    from importlib.metadata import version  # pylint: disable=E


def test_run_aws_head_bucket(monkeypatch):
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


def test_run_aws_version():
    """Test ``runway run-aws --version``."""
    runner = CliRunner()
    result = runner.invoke(cli, ["run-aws", "--version"])
    assert result.exit_code == 0
    assert version("awscli") in result.output


def test_run_aws_version_separator():
    """Test ``runway run-aws -- --version``."""
    runner = CliRunner()
    result = runner.invoke(cli, ["run-aws", "--", "--version"])
    assert result.exit_code == 0
    assert version("awscli") in result.output
