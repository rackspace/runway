"""Test runway.cfngin.hooks.staticsite.upload_staticsite."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
import yaml
from botocore.stub import ANY

from runway.cfngin.hooks.staticsite.upload_staticsite import (
    auto_detect_content_type,
    calculate_hash_of_extra_files,
    get_content,
    get_content_type,
    sync_extra_files,
)
from runway.module.staticsite.options import RunwayStaticSiteExtraFileDataModel

if TYPE_CHECKING:
    from ....factories import MockCfnginContext


@pytest.mark.parametrize(
    "provided, expected",
    [
        ("prefix.test.json", "application/json"),
        ("test.json", "application/json"),
        ("test.yml", "text/yaml"),
        ("test.yaml", "text/yaml"),
        ("test.txt", None),
        ("test", None),
        (".test", None),
    ],
)
def test_auto_detect_content_type(provided: str, expected: str | None) -> None:
    """Test auto_detect_content_type."""
    assert auto_detect_content_type(provided) == expected


@pytest.mark.parametrize(
    "provided, expected",
    [
        (
            RunwayStaticSiteExtraFileDataModel.model_construct(
                content_type="text/plain", name="test.txt"
            ),
            "text/plain",
        ),
        (
            RunwayStaticSiteExtraFileDataModel.model_construct(
                name="test.txt", content_type="text/plain"
            ),
            "text/plain",
        ),
        (
            RunwayStaticSiteExtraFileDataModel.model_construct(name="test.json"),
            "application/json",
        ),
        (RunwayStaticSiteExtraFileDataModel.model_construct(name="test.txt"), None),
    ],
)
def test_get_content_type(
    provided: RunwayStaticSiteExtraFileDataModel, expected: str | None
) -> None:
    """Test get_content_type."""
    assert get_content_type(provided) == expected


def test_get_content_json() -> None:
    """Get content JSON."""
    content = {"a": 0}

    actual = get_content(
        RunwayStaticSiteExtraFileDataModel(
            content_type="application/json", content=content, name=""
        )
    )
    expected = json.dumps(content)

    assert actual == expected


def test_get_content_yaml() -> None:
    """Get content YAML."""
    content = {"a": 0}

    actual = get_content(
        RunwayStaticSiteExtraFileDataModel(content_type="text/yaml", content=content, name="")
    )
    expected = yaml.safe_dump(content)

    assert actual == expected


def test_get_content_unknown() -> None:
    """Get content unknown."""
    with pytest.raises(ValueError):  # noqa: PT011
        get_content(RunwayStaticSiteExtraFileDataModel(content={"a": 0}, name=""))


def test_get_content_unsupported() -> None:
    """Get content unknown."""
    with pytest.raises(TypeError):
        get_content(RunwayStaticSiteExtraFileDataModel(content=123, name=""))


@pytest.mark.parametrize(
    "a, b",
    [
        (
            RunwayStaticSiteExtraFileDataModel.model_construct(name="a"),
            RunwayStaticSiteExtraFileDataModel.model_construct(name="b"),
        ),
        (
            RunwayStaticSiteExtraFileDataModel.model_construct(name="test", content_type="a"),
            RunwayStaticSiteExtraFileDataModel.model_construct(name="test", content_type="b"),
        ),
        (
            RunwayStaticSiteExtraFileDataModel.model_construct(name="test", content="a"),
            RunwayStaticSiteExtraFileDataModel.model_construct(name="test", content="b"),
        ),
    ],
)
def test_calculate_hash_of_extra_files(
    a: RunwayStaticSiteExtraFileDataModel, b: RunwayStaticSiteExtraFileDataModel
) -> None:
    """Test calculate_hash_of_extra_files."""
    assert calculate_hash_of_extra_files([a]) != calculate_hash_of_extra_files([b])


def test_sync_extra_files_json_content(cfngin_context: MockCfnginContext) -> None:
    """Test sync_extra_files json content is put in s3."""
    s3_stub = cfngin_context.add_stubber("s3")

    content = {"a": 0}

    s3_stub.add_response(
        "put_object",
        {},
        {
            "Bucket": "bucket",
            "Key": "test.json",
            "Body": json.dumps(content).encode(),
            "ContentType": "application/json",
        },
    )

    files = [RunwayStaticSiteExtraFileDataModel(name="test.json", content=content)]

    with s3_stub as stub:
        assert sync_extra_files(cfngin_context, "bucket", extra_files=files) == ["test.json"]
        stub.assert_no_pending_responses()


def test_sync_extra_files_yaml_content(cfngin_context: MockCfnginContext) -> None:
    """Test sync_extra_files yaml content is put in s3."""
    s3_stub = cfngin_context.add_stubber("s3")

    content = {"a": 0}

    s3_stub.add_response(
        "put_object",
        {},
        {
            "Bucket": "bucket",
            "Key": "test.yaml",
            "Body": yaml.safe_dump(content).encode(),
            "ContentType": "text/yaml",
        },
    )

    files = [RunwayStaticSiteExtraFileDataModel.model_construct(name="test.yaml", content=content)]

    with s3_stub as stub:
        assert sync_extra_files(cfngin_context, "bucket", extra_files=files) == ["test.yaml"]
        stub.assert_no_pending_responses()


def test_sync_extra_files_empty_content(cfngin_context: MockCfnginContext) -> None:
    """Test sync_extra_files empty content is not uploaded."""
    s3_stub = cfngin_context.add_stubber("s3")

    with s3_stub as stub:
        result = sync_extra_files(
            cfngin_context,
            "bucket",
            extra_files=[
                RunwayStaticSiteExtraFileDataModel.model_construct(name="test.yaml", content="")
            ],
        )
        assert isinstance(result, list)
        assert not result
        stub.assert_no_pending_responses()


def test_sync_extra_files_file_reference(cfngin_context: MockCfnginContext) -> None:
    """Test sync_extra_files file is uploaded."""
    s3_stub = cfngin_context.add_stubber("s3")

    # This isn't ideal, but needed to get the correct stubbing.
    # Stubber doesn't support 'upload_file' so we need to assume it delegates to 'put_object'.
    # https://stackoverflow.com/questions/59303423/s3-boto3-stubber-doesnt-have-mapping-for-download-file
    s3_stub.add_response(
        "put_object",
        {},
        {
            "Bucket": "bucket",
            "Key": "test",
            # Don't want to make any more assumptions about how upload_file works
            "Body": ANY,
        },
    )

    files = [RunwayStaticSiteExtraFileDataModel.model_construct(name="test", file=".gitignore")]

    with s3_stub as stub:
        assert sync_extra_files(cfngin_context, "bucket", extra_files=files) == ["test"]
        stub.assert_no_pending_responses()


def test_sync_extra_files_file_reference_with_content_type(
    cfngin_context: MockCfnginContext,
) -> None:
    """Test sync_extra_files file is uploaded with the content type."""
    s3_stub = cfngin_context.add_stubber("s3")

    s3_stub.add_response(
        "put_object",
        {},
        {
            "Bucket": "bucket",
            "Key": "test.json",
            "Body": ANY,
            "ContentType": "application/json",
        },
    )

    files = [
        RunwayStaticSiteExtraFileDataModel.model_construct(name="test.json", file=".gitignore")
    ]

    with s3_stub as stub:
        assert sync_extra_files(cfngin_context, "bucket", extra_files=files) == ["test.json"]
        stub.assert_no_pending_responses()


def test_sync_extra_files_hash_unchanged(cfngin_context: MockCfnginContext) -> None:
    """Test sync_extra_files upload is skipped if the has was unchanged."""
    s3_stub = cfngin_context.add_stubber("s3")
    ssm_stub = cfngin_context.add_stubber("ssm")

    extra = RunwayStaticSiteExtraFileDataModel.model_construct(name="test", content="test")
    extra_hash = calculate_hash_of_extra_files([extra])

    ssm_stub.add_response(
        "get_parameter",
        {"Parameter": {"Value": extra_hash}},
        {"Name": "hash_nameextra"},
    )

    with s3_stub as s3_stub, ssm_stub as ssm_stub:
        result = sync_extra_files(
            cfngin_context,
            "bucket",
            extra_files=[extra],
            hash_tracking_parameter="hash_name",
        )
        assert isinstance(result, list)
        assert not result
        s3_stub.assert_no_pending_responses()
        ssm_stub.assert_no_pending_responses()


def test_sync_extra_files_hash_updated(cfngin_context: MockCfnginContext) -> None:
    """Test sync_extra_files extra files hash is updated."""
    s3_stub = cfngin_context.add_stubber("s3")
    ssm_stub = cfngin_context.add_stubber("ssm")

    extra = RunwayStaticSiteExtraFileDataModel(
        name="test", content="test", content_type="text/plain"
    )
    extra_hash = calculate_hash_of_extra_files([extra])

    ssm_stub.add_response(
        "get_parameter",
        {"Parameter": {"Value": "old value"}},
        {"Name": "hash_nameextra"},
    )

    ssm_stub.add_response(
        "put_parameter",
        {},
        {
            "Name": "hash_nameextra",
            "Description": ANY,
            "Value": extra_hash,
            "Type": "String",
            "Overwrite": True,
        },
    )

    s3_stub.add_response(
        "put_object",
        {},
        {
            "Bucket": "bucket",
            "Key": "test",
            "Body": b"test",
            "ContentType": "text/plain",
        },
    )

    with s3_stub as s3_stub, ssm_stub as ssm_stub:
        assert sync_extra_files(
            cfngin_context,
            "bucket",
            extra_files=[extra],
            hash_tracking_parameter="hash_name",
        ) == ["test"]
        s3_stub.assert_no_pending_responses()
        ssm_stub.assert_no_pending_responses()
