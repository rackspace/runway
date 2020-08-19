"""Test runway.hooks.staticsite.upload_staticsite."""
# pylint: disable=no-self-use,unused-import,too-few-public-methods
import json

import pytest
import yaml
from botocore.stub import ANY

from runway.hooks.staticsite.upload_staticsite import (
    auto_detect_content_type,
    calculate_hash_of_extra_files,
    get_content,
    get_content_type,
    sync_extra_files,
)


class TestAutoDetectContentType(object):
    """Test runway.hooks.staticsite.upload_staticsite.auto_detect_content_type."""

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
    def test_auto_detect_content_type(self, provided, expected):
        """Test auto_detect_content_type."""
        assert auto_detect_content_type(provided) == expected


class TestGetContentType(object):
    """Test runway.hooks.staticsite.upload_staticsite.get_content_type."""

    @pytest.mark.parametrize(
        "provided, expected",
        [
            ({"name": "test.txt", "content_type": "text/plain"}, "text/plain"),
            ({"name": "test.json"}, "application/json"),
            ({"name": "test.txt"}, None),
        ],
    )
    def test_get_content_type(self, provided, expected):
        """Test get_content_type."""
        assert get_content_type(provided) == expected


class TestGetContent(object):
    """Test runway.hooks.staticsite.upload_staticsite.get_content."""

    def test_json_content(self):
        """Test json content is serialized."""
        content = {"a": 0}

        actual = get_content({"content_type": "application/json", "content": content})
        expected = json.dumps(content)

        assert actual == expected

    def test_yaml_content(self):
        """Test yaml content is serialized."""
        content = {"a": 0}

        actual = get_content({"content_type": "text/yaml", "content": content})
        expected = yaml.safe_dump(content)

        assert actual == expected

    def test_unknown_content_type(self):
        """Test content w/out content_type."""
        with pytest.raises(ValueError):
            get_content({"content": {"a": 0}})

    def test_unsupported_content_type(self):
        """Test content w/unsupported content."""
        with pytest.raises(TypeError):
            get_content({"content": 123})


class TestCalculateExtraFilesHash(object):
    """Test runway.hooks.staticsite.upload_staticsite.calculate_hash_of_extra_files."""

    @pytest.mark.parametrize(
        "a, b",
        [
            ({"name": "a"}, {"name": "b"}),
            (
                {"name": "test", "content_type": "a"},
                {"name": "test", "content_type": "b"},
            ),
            ({"name": "test", "content": "a"}, {"name": "test", "content": "b"}),
        ],
    )
    def test_calculate_hash_of_extra_files(self, a, b):
        """Test calculate_hash_of_extra_files."""
        assert calculate_hash_of_extra_files([a]) != calculate_hash_of_extra_files([b])


class TestSyncExtraFiles(object):
    """Test runway.hooks.staticsite.upload_staticsite.sync_extra_files."""

    def test_json_content(self, cfngin_context):
        """Test json content is put in s3."""
        s3_stub = cfngin_context.add_stubber("s3")

        content = {"a": 0}

        s3_stub.add_response(
            "put_object",
            {},
            {
                "Bucket": "bucket",
                "Key": "test.json",
                "Body": json.dumps(content),
                "ContentType": "application/json",
            },
        )

        files = [{"name": "test.json", "content": content}]

        with s3_stub as stub:
            assert sync_extra_files(cfngin_context, "bucket", extra_files=files) == [
                "test.json"
            ]
            stub.assert_no_pending_responses()

    def test_yaml_content(self, cfngin_context):
        """Test yaml content is put in s3."""
        s3_stub = cfngin_context.add_stubber("s3")

        content = {"a": 0}

        s3_stub.add_response(
            "put_object",
            {},
            {
                "Bucket": "bucket",
                "Key": "test.yaml",
                "Body": yaml.safe_dump(content),
                "ContentType": "text/yaml",
            },
        )

        files = [{"name": "test.yaml", "content": content}]

        with s3_stub as stub:
            assert sync_extra_files(cfngin_context, "bucket", extra_files=files) == [
                "test.yaml"
            ]
            stub.assert_no_pending_responses()

    def test_empty_content(self, cfngin_context):
        """Test empty content is not uploaded."""
        s3_stub = cfngin_context.add_stubber("s3")

        files = [{"name": "test.yaml", "content": {}}]

        with s3_stub as stub:
            assert sync_extra_files(cfngin_context, "bucket", extra_files=files) == []
            stub.assert_no_pending_responses()

    def test_file_reference(self, cfngin_context):
        """Test file is uploaded."""
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

        files = [{"name": "test", "file": "Pipfile"}]

        with s3_stub as stub:
            assert sync_extra_files(cfngin_context, "bucket", extra_files=files) == [
                "test"
            ]
            stub.assert_no_pending_responses()

    def test_file_reference_with_content_type(self, cfngin_context):
        """Test file is uploaded with the content type."""
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

        files = [{"name": "test.json", "file": "Pipfile"}]

        with s3_stub as stub:
            assert sync_extra_files(cfngin_context, "bucket", extra_files=files) == [
                "test.json"
            ]
            stub.assert_no_pending_responses()

    def test_hash_unchanged(self, cfngin_context):
        """Test upload is skipped if the has was unchanged."""
        s3_stub = cfngin_context.add_stubber("s3")
        ssm_stub = cfngin_context.add_stubber("ssm")

        extra = {"name": "test", "content": "test"}
        extra_hash = calculate_hash_of_extra_files([extra])

        ssm_stub.add_response(
            "get_parameter",
            {"Parameter": {"Value": extra_hash}},
            {"Name": "hash_nameextra"},
        )

        with s3_stub as s3_stub, ssm_stub as ssm_stub:
            assert (
                sync_extra_files(
                    cfngin_context,
                    "bucket",
                    extra_files=[extra],
                    hash_tracking_parameter="hash_name",
                )
                == []
            )
            s3_stub.assert_no_pending_responses()
            ssm_stub.assert_no_pending_responses()

    def test_hash_updated(self, cfngin_context):
        """Test extra files hash is updated."""
        s3_stub = cfngin_context.add_stubber("s3")
        ssm_stub = cfngin_context.add_stubber("ssm")

        extra = {"name": "test", "content": "test", "content_type": "text/plain"}
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
                "Body": "test",
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
