"""Test AWS Lambda hook."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from pydantic import model_validator

from runway._cli import cli
from runway.compat import cached_property
from runway.utils import BaseModel

if TYPE_CHECKING:
    from collections.abc import Generator

    import boto3
    from click.testing import CliRunner, Result
    from mypy_boto3_cloudformation.client import CloudFormationClient
    from mypy_boto3_cloudformation.type_defs import StackTypeDef
    from mypy_boto3_lambda.client import LambdaClient

    from runway.context import RunwayContext

    from .sample_app.src.type_defs import LambdaResponse

AWS_REGION = "us-east-1"
PYTHON_RUNTIME = "python3.10"
STACK_PREFIX = "test-awslambda"

CURRENT_DIR = Path(__file__).parent
SRC_DIR = CURRENT_DIR / "sample_app" / "src"
DOCKER_MYSQL_DIR = SRC_DIR / "docker_mysql"
DOCKER_XMLSEC_DIR = SRC_DIR / "docker_xmlsec"

ENV_VARS = {
    "CI": "1",
    "PYTHON_RUNTIME": PYTHON_RUNTIME,
    "PIPENV_VENV_IN_PROJECT": "1",
    "PIPENV_VERBOSITY": "-1",
    "POETRY_VIRTUALENVS_IN_PROJECT": "true",
    "PYXMLSEC_STATIC_DEPS": "1",
}


pytestmark = pytest.mark.skipif(
    not shutil.which("mysql_config"),
    reason="mysql_config CLI from mysql OS package must be installed and in PATH",
)


class AwslambdaStackOutputs(BaseModel):
    """Outputs of a Stack used for testing the awslambda hook."""

    CodeImageUri: str | None = None
    CodeS3Bucket: str
    CodeS3Key: str
    CodeS3ObjectVersion: str | None = None
    CodeZipFile: str | None = None
    LambdaFunction: str
    LambdaFunctionArn: str
    LambdaRole: str
    LayerContentS3Bucket: str | None = None
    LayerContentS3Key: str | None = None
    LayerContentS3ObjectVersion: str | None = None
    LayerVersion: str | None = None
    Runtime: str

    @model_validator(mode="before")
    @classmethod
    def _convert_null_to_none(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Convert ``null`` to ``NoneType``."""

        def _handle_null(v: Any) -> Any:
            if v == "null":
                return None
            return v

        return {k: _handle_null(v) for k, v in values.items()}


class AwslambdaTester:
    """Class to simplify testing the awslambda hook's results."""

    def __init__(self, session: boto3.Session, stack_name: str) -> None:
        """Instantiate class."""
        self._session = session
        self.stack_name = stack_name

    @cached_property
    def cfn_client(self) -> CloudFormationClient:
        """AWS CloudFormation client."""
        return self._session.client("cloudformation")

    @cached_property
    def client(self) -> LambdaClient:
        """AWS Lambda client."""
        return self._session.client("lambda")

    @cached_property
    def outputs(self) -> AwslambdaStackOutputs:
        """Stack outputs."""
        return AwslambdaStackOutputs.model_validate(
            {
                output["OutputKey"]: output["OutputValue"]
                for output in self.stack.get("Outputs", [])
                if "OutputKey" in output and "OutputValue" in output
            }
        )

    @cached_property
    def stack(self) -> StackTypeDef:
        """AWS Lambda Function CloudFormation Stack data."""
        stacks = self.cfn_client.describe_stacks(StackName=self.stack_name)["Stacks"]
        if not stacks:
            raise ValueError(
                f"Stack {self.stack_name} not found in region {self._session.region_name}"
            )
        return stacks[0]

    def invoke(self, *, payload: str | None = None) -> LambdaResponse:
        """Invoke the Lambda Function."""
        response = self.client.invoke(
            FunctionName=self.outputs.LambdaFunction,
            InvocationType="RequestResponse",
            **{"Payload": payload} if payload else {},  # pyright: ignore[reportArgumentType]
        )
        if "Payload" in response:
            return json.load(response["Payload"])
        raise ValueError("Lambda Function did not return a payload")


def assert_runtime(tester: AwslambdaTester, runtime: str) -> None:
    """Assert that the deployment package is using the expected runtime."""
    assert tester.outputs.Runtime == runtime


def assert_uploaded(tester: AwslambdaTester, deploy_result: Result) -> None:
    """Assert that the deployment package was uploaded."""
    uri = f"s3://{tester.outputs.CodeS3Bucket}/{tester.outputs.CodeS3Key}"
    assert f"uploading deployment package {uri}..." in deploy_result.stdout, "\n".join(
        line for line in deploy_result.stdout.split("\n") if uri in line
    )


@pytest.fixture(scope="module")
def deploy_result(cli_runner: CliRunner) -> Generator[Result, None, None]:
    """Execute `runway deploy` with `runway destroy` as a cleanup step."""
    yield cli_runner.invoke(cli, ["deploy"], env=ENV_VARS)
    assert cli_runner.invoke(cli, ["destroy"], env=ENV_VARS).exit_code == 0
    shutil.rmtree(CURRENT_DIR / ".runway", ignore_errors=True)
    shutil.rmtree(CURRENT_DIR / "sample_app" / ".runway", ignore_errors=True)
    # remove .venv/ & *.lock from source code directories - more important for local testing
    (DOCKER_MYSQL_DIR / "Pipfile.lock").unlink(missing_ok=True)
    (DOCKER_XMLSEC_DIR / "poetry.lock").unlink(missing_ok=True)
    for subdir in [DOCKER_MYSQL_DIR, DOCKER_XMLSEC_DIR]:
        shutil.rmtree(subdir / ".venv", ignore_errors=True)


@pytest.mark.order("first")
def test_deploy_exit_code(deploy_result: Result) -> None:
    """Test deploy exit code."""
    assert deploy_result.exit_code == 0, deploy_result.output


def test_deploy_log_messages(deploy_result: Result) -> None:
    """Test deploy log messages."""
    build_skipped = [line for line in deploy_result.stdout.split("\n") if "build skipped" in line]
    assert not build_skipped, "\n".join(build_skipped)


def test_docker(deploy_result: Result, namespace: str, runway_context: RunwayContext) -> None:
    """Test function built with Docker."""
    tester = AwslambdaTester(
        runway_context.get_session(region=AWS_REGION),
        f"{namespace}-{STACK_PREFIX}-docker",
    )
    assert_runtime(tester, PYTHON_RUNTIME)
    assert_uploaded(tester, deploy_result)
    response = tester.invoke()
    response_str = json.dumps(response, indent=4, sort_keys=True)
    assert response["code"] == 200, response_str
    assert response["data"]["requests"]
    assert "index.py" in response["data"]["dir_contents"]
    assert "urllib3/__init__.py" in response["data"]["dir_contents"]
    assert "requests/__init__.py" in response["data"]["dir_contents"]
    assert "charset_normalizer/__init__.py" in response["data"]["dir_contents"]
    assert "certifi/__init__.py" in response["data"]["dir_contents"]


def test_local(deploy_result: Result, namespace: str, runway_context: RunwayContext) -> None:
    """Test function built with local python."""
    tester = AwslambdaTester(
        runway_context.get_session(region=AWS_REGION),
        f"{namespace}-{STACK_PREFIX}-local",
    )
    assert_runtime(tester, PYTHON_RUNTIME)
    assert_uploaded(tester, deploy_result)
    response = tester.invoke()
    assert response["code"] == 200
    assert response["data"]["dir_contents"] == ["index.py"]


def test_mysql(deploy_result: Result, namespace: str, runway_context: RunwayContext) -> None:
    """Test function built from Dockerfile for mysql."""
    tester = AwslambdaTester(
        runway_context.get_session(region=AWS_REGION),
        f"{namespace}-{STACK_PREFIX}-mysql",
    )
    assert_runtime(tester, "python3.10")
    assert_uploaded(tester, deploy_result)
    response = tester.invoke()
    response_str = json.dumps(response, indent=4, sort_keys=True)
    assert response["code"] == 200, response_str
    assert len(response["data"]["mysqlclient"]) >= 10
    assert "Pipfile" not in response["data"]["dir_contents"]


def test_xmlsec(deploy_result: Result, namespace: str, runway_context: RunwayContext) -> None:
    """Test function built from Dockerfile for xmlsec."""
    tester = AwslambdaTester(
        runway_context.get_session(region=AWS_REGION),
        f"{namespace}-{STACK_PREFIX}-xmlsec",
    )
    assert_runtime(tester, "python3.10")
    assert_uploaded(tester, deploy_result)
    response = tester.invoke()
    response_str = json.dumps(response, indent=4, sort_keys=True)
    assert response["code"] == 200, response_str
    assert "etree" in response["data"]["lxml"]
    assert "KeysManager" in response["data"]["xmlsec"]
    assert ".gitignore" not in response["data"]["dir_contents"]
    assert "poetry.lock" not in response["data"]["dir_contents"]


def test_xmlsec_layer(deploy_result: Result, namespace: str, runway_context: RunwayContext) -> None:
    """Test layer built from Dockerfile for xmlsec."""
    tester = AwslambdaTester(
        runway_context.get_session(region=AWS_REGION),
        f"{namespace}-{STACK_PREFIX}-xmlsec-layer",
    )
    assert_runtime(tester, "python3.10")
    assert_uploaded(tester, deploy_result)
    response = tester.invoke()
    response_str = json.dumps(response, indent=4, sort_keys=True)
    assert response["code"] == 200, response_str
    assert "etree" in response["data"]["lxml"]
    assert "KeysManager" in response["data"]["xmlsec"]
    assert response["data"]["dir_contents"] == ["index.py"]


def test_plan(cli_runner: CliRunner, deploy_result: Result) -> None:  # noqa: ARG001
    """Test ``runway plan`` - this was not possible with old hook.

    deploy_result required so cleanup does not start before this runs.

    """
    # remove *.lock files to prevent change in source hash
    (DOCKER_MYSQL_DIR / "Pipfile.lock").unlink(missing_ok=True)
    (DOCKER_XMLSEC_DIR / "poetry.lock").unlink(missing_ok=True)
    plan_results = cli_runner.invoke(cli, ["plan"], env=ENV_VARS)
    assert plan_results.exit_code == 0, plan_results.output
    matches = [line for line in plan_results.stdout.split("\n") if line.endswith(":no changes")]
    a_list = [4, 5]
    # count needs to be updated if number of test stacks change
    assert len(matches) in a_list, "\n".join(matches)
