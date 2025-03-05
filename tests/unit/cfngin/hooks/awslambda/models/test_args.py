"""Test runway.cfngin.hooks.awslambda.models.args."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from runway.cfngin.hooks.awslambda.models.args import (
    AwsLambdaHookArgs,
    DockerOptions,
    PythonHookArgs,
)

MODULE = "runway.cfngin.hooks.awslambda.models.args"


class TestAwsLambdaHookArgs:
    """Test AwsLambdaHookArgs."""

    def test___resolve_path(self) -> None:
        """Test _resolve_path."""
        obj = AwsLambdaHookArgs(  # these are all required fields
            bucket_name="test-bucket",
            runtime="test",
            source_code="./",  # type: ignore
        )
        assert obj.source_code.is_absolute()
        assert obj.source_code == Path.cwd()

    def test__validate_runtime_or_docker(self, tmp_path: Path) -> None:
        """Test _validate_runtime_or_docker."""
        obj = AwsLambdaHookArgs(
            bucket_name="test-bucket",
            runtime="test",
            source_code=tmp_path,
        )
        assert obj.runtime == "test"

    @pytest.mark.parametrize(
        "kwargs", [{"image": "test"}, {"file": ""}, {"file": "", "image": "test"}]
    )
    def test__validate_runtime_or_docker_docker_no_runtime(
        self, kwargs: dict[str, Any], tmp_path: Path
    ) -> None:
        """Test _validate_runtime_or_docker no runtime if Docker."""
        if "file" in kwargs:
            dockerfile = tmp_path / "Dockerfile"
            dockerfile.touch()  # file has to exist
            kwargs["file"] = dockerfile
        obj = AwsLambdaHookArgs(
            bucket_name="test-bucket",
            docker=DockerOptions.model_validate(kwargs),
            source_code=tmp_path,
        )
        assert not obj.runtime

    def test__validate_runtime_or_docker_docker_disabled(self, tmp_path: Path) -> None:
        """Test _validate_runtime_or_docker.

        With ``runtime=None`` and ``docker.disabled=True``.

        """
        with pytest.raises(
            ValidationError,
            match="runtime\n  Value error, runtime must be provided if docker.disabled is True",
        ):
            AwsLambdaHookArgs(
                bucket_name="test-bucket",
                docker=DockerOptions(disabled=True),
                source_code=tmp_path,
            )

    def test__validate_runtime_or_docker_no_runtime_or_docker(self, tmp_path: Path) -> None:
        """Test _validate_runtime_or_docker no runtime or docker."""
        with pytest.raises(
            ValidationError,
            match="runtime\n  Value error, docker.file, docker.image, or runtime is required",
        ):
            AwsLambdaHookArgs(
                bucket_name="test-bucket",
                source_code=tmp_path,
            )

    def test_field_defaults(self, tmp_path: Path) -> None:
        """Test field defaults."""
        obj = AwsLambdaHookArgs(  # these are all required fields
            bucket_name="test-bucket",
            runtime="test",
            source_code=tmp_path,
        )
        assert not obj.extend_gitignore
        assert isinstance(obj.extend_gitignore, list)
        assert not obj.object_prefix

    def test_source_code_is_file(self, tmp_path: Path) -> None:
        """Test source_code is file."""
        source_path = tmp_path / "foo"
        source_path.write_text("bar")
        with pytest.raises(
            ValidationError,
            match="source_code\n  Path does not point to a directory",
        ):
            AwsLambdaHookArgs(  # these are all required fields
                bucket_name="test-bucket",
                runtime="test",
                source_code=source_path,
            )

    def test_source_code_not_exist(self, tmp_path: Path) -> None:
        """Test source_code directory does not exist."""
        source_path = tmp_path / "foo"
        with pytest.raises(
            ValidationError,
            match="source_code\n  Path does not point to a directory",
        ):
            AwsLambdaHookArgs(  # these are all required fields
                bucket_name="test-bucket",
                runtime="test",
                source_code=source_path,
            )


class TestPythonHookArgs:
    """Test PythonHookArgs."""

    @pytest.mark.parametrize("arg_flag", ["-r", "--requirement"])
    def test__validate_extend_pip_args_no_requirement(self, arg_flag: str, tmp_path: Path) -> None:
        """Test _validate_extend_pip_args_no_requirement."""
        with pytest.raises(
            ValidationError,
            match="extend_pip_args\n  "
            "Value error, can't contain '--requirement' or '-r'; conflicts with arguments provided by the hook",
        ):
            PythonHookArgs(
                bucket_name="test-bucket",
                extend_pip_args=[arg_flag, "foo.txt"],
                runtime="test",
                source_code=tmp_path,
            )

    @pytest.mark.parametrize("arg_flag", ["-t", "--target"])
    def test__validate_extend_pip_args_no_target(self, arg_flag: str, tmp_path: Path) -> None:
        """Test _validate_extend_pip_args_no_target."""
        with pytest.raises(
            ValidationError,
            match="extend_pip_args\n  "
            "Value error, can't contain '--target' or '-t'; conflicts with arguments provided by the hook",
        ):
            PythonHookArgs(
                bucket_name="test-bucket",
                extend_pip_args=[arg_flag, "/tmp/foo"],
                runtime="test",
                source_code=tmp_path,
            )

    def test_extra(self, tmp_path: Path) -> None:
        """Test extra fields."""
        obj = PythonHookArgs(
            bucket_name="test-bucket",
            invalid=True,  # type: ignore
            runtime="test",
            source_code=tmp_path,
        )
        assert not obj.get("invalid")

    def test_field_defaults(self, tmp_path: Path) -> None:
        """Test field defaults."""
        obj = PythonHookArgs(  # these are all required fields
            bucket_name="test-bucket",
            runtime="test",
            source_code=tmp_path,
        )
        assert not obj.extend_pip_args
        assert obj.use_pipenv
        assert obj.use_poetry
