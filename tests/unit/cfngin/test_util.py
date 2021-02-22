"""Tests for runway.cfngin.util."""
# pylint: disable=unused-argument,invalid-name
# pyright: basic
from __future__ import annotations

import unittest
from pathlib import Path
from typing import Any, List

import boto3
import mock
import pytest
from pydantic import ValidationError

from runway.cfngin.util import (
    Extractor,
    SourceProcessor,
    TarExtractor,
    TarGzipExtractor,
    ZipExtractor,
    camel_to_snake,
    cf_safe_name,
    get_client_region,
    get_s3_endpoint,
    parse_cloudformation_template,
    read_value_from_path,
    s3_bucket_location_constraint,
    yaml_to_ordered_dict,
)
from runway.config.models.cfngin import GitCfnginPackageSourceDefinitionModel

AWS_REGIONS = [
    "us-east-1",
    "cn-north-1",
    "ap-northeast-1",
    "eu-west-1",
    "ap-southeast-1",
    "ap-southeast-2",
    "us-west-2",
    "us-gov-west-1",
    "us-west-1",
    "eu-central-1",
    "sa-east-1",
]


def mock_create_cache_directories(self: Any, **kwargs: Any) -> int:
    """Mock create cache directories.

    Don't actually need the directories created in testing

    """
    return 1


def test_read_value_from_path_abs(tmp_path: Path) -> None:
    """Test read_value_from_path absolute path."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("success")
    assert read_value_from_path(f"file://{test_file.absolute()}") == "success"


def test_read_value_from_path_dir(tmp_path: Path) -> None:
    """Test read_value_from_path direcory."""
    with pytest.raises(ValueError):
        read_value_from_path(f"file://{tmp_path.absolute()}")


def test_read_value_from_path_not_exist(tmp_path: Path) -> None:
    """Test read_value_from_path does not exist."""
    with pytest.raises(ValueError):
        read_value_from_path(f"file://{(tmp_path / 'something.txt').absolute()}")


def test_read_value_from_path_no_root_path(cd_tmp_path: Path) -> None:
    """Test read_value_from_path no root_path."""
    test_file = cd_tmp_path / "test.txt"
    test_file.write_text("success")
    assert read_value_from_path(f"file://./{test_file.name}") == "success"


def test_read_value_from_path_root_path_dir(tmp_path: Path) -> None:
    """Test read_value_from_path root_path is dir."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("success")
    assert (
        read_value_from_path(f"file://./{test_file.name}", root_path=tmp_path)
        == "success"
    )


def test_read_value_from_path_root_path_file(tmp_path: Path) -> None:
    """Test read_value_from_path root_path is file."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("success")
    assert (
        read_value_from_path(
            f"file://./{test_file.name}", root_path=tmp_path / "something.json"
        )
        == "success"
    )


class TestUtil(unittest.TestCase):
    """Tests for runway.cfngin.util."""

    def test_cf_safe_name(self) -> None:
        """Test cf safe name."""
        tests = (("abc-def", "AbcDef"), ("GhI", "GhI"), ("jKlm.noP", "JKlmNoP"))
        for test in tests:
            self.assertEqual(cf_safe_name(test[0]), test[1])

    def test_camel_to_snake(self) -> None:
        """Test camel to snake."""
        tests = (
            ("TestTemplate", "test_template"),
            ("testTemplate", "test_template"),
            ("test_Template", "test__template"),
            ("testtemplate", "testtemplate"),
        )
        for test in tests:
            self.assertEqual(camel_to_snake(test[0]), test[1])

    def test_yaml_to_ordered_dict(self) -> None:
        """Test yaml to ordered dict."""
        raw_config = """
        pre_deploy:
          hook2:
            path: foo.bar
          hook1:
            path: foo1.bar1
        """
        config = yaml_to_ordered_dict(raw_config)
        self.assertEqual(list(config["pre_deploy"].keys())[0], "hook2")
        self.assertEqual(config["pre_deploy"]["hook2"]["path"], "foo.bar")

    def test_get_client_region(self) -> None:
        """Test get client region."""
        regions = ["us-east-1", "us-west-1", "eu-west-1", "sa-east-1"]
        for region in regions:
            client = boto3.client("s3", region_name=region)
            self.assertEqual(get_client_region(client), region)

    def test_get_s3_endpoint(self) -> None:
        """Test get s3 endpoint."""
        endpoint_url = "https://example.com"
        client = boto3.client("s3", region_name="us-east-1", endpoint_url=endpoint_url)
        self.assertEqual(get_s3_endpoint(client), endpoint_url)

    def test_s3_bucket_location_constraint(self) -> None:
        """Test s3 bucket location constraint."""
        tests = (("us-east-1", ""), ("us-west-1", "us-west-1"))
        for region, result in tests:
            self.assertEqual(s3_bucket_location_constraint(region), result)

    def test_parse_cloudformation_template(self) -> None:
        """Test parse cloudformation template."""
        template = """AWSTemplateFormatVersion: "2010-09-09"
Parameters:
  Param1:
    Type: String
Resources:
  Bucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName:
        !Join
          - "-"
          - - !Ref "AWS::StackName"
            - !Ref "AWS::Region"
Outputs:
  DummyId:
    Value: dummy-1234"""
        parsed_template = {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Outputs": {"DummyId": {"Value": "dummy-1234"}},
            "Parameters": {"Param1": {"Type": "String"}},
            "Resources": {
                "Bucket": {
                    "Type": "AWS::S3::Bucket",
                    "Properties": {
                        "BucketName": {
                            u"Fn::Join": [
                                "-",
                                [{u"Ref": u"AWS::StackName"}, {u"Ref": u"AWS::Region"}],
                            ]
                        }
                    },
                }
            },
        }
        self.assertEqual(parse_cloudformation_template(template), parsed_template)

    def test_extractors(self):
        """Test extractors."""
        self.assertEqual(Extractor(Path("test.zip")).archive, Path("test.zip"))
        self.assertEqual(TarExtractor().extension, ".tar")
        self.assertEqual(TarGzipExtractor().extension, ".tar.gz")
        self.assertEqual(ZipExtractor().extension, ".zip")
        for i in [TarExtractor(), ZipExtractor(), ZipExtractor()]:
            i.set_archive(Path("/tmp/foo"))
            self.assertEqual(i.archive.name.endswith(i.extension), True)  # type: ignore

    def test_SourceProcessor_helpers(self):  # noqa: N802
        """Test SourceProcessor helpers."""
        with mock.patch.object(
            SourceProcessor,
            "create_cache_directories",
            new=mock_create_cache_directories,
        ):
            sp = SourceProcessor(sources={})  # type: ignore

            self.assertEqual(
                sp.sanitize_git_path("git@github.com:foo/bar.git"),
                "git_github.com_foo_bar",
            )
            self.assertEqual(
                sp.sanitize_uri_path("http://example.com/foo/bar.gz@1"),
                "http___example.com_foo_bar.gz_1",
            )
            self.assertEqual(
                sp.sanitize_git_path("git@github.com:foo/bar.git", "v1"),
                "git_github.com_foo_bar-v1",
            )
            self.assertEqual(
                sp.determine_git_ls_remote_ref(
                    GitCfnginPackageSourceDefinitionModel(branch="foo", uri="test")
                ),
                "refs/heads/foo",
            )
            for i in [{}, {"tag": "foo"}, {"commit": "1234"}]:
                self.assertEqual(
                    sp.determine_git_ls_remote_ref(
                        GitCfnginPackageSourceDefinitionModel(uri="git@foo", **i)
                    ),
                    "HEAD",
                )

            self.assertEqual(
                sp.git_ls_remote(
                    "https://github.com/remind101/stacker.git", "refs/heads/release-1.0"
                ),
                "857b4834980e582874d70feef77bb064b60762d1",
            )

            bad_configs = [
                {"uri": "x", "commit": "1234", "tag": "v1", "branch": "x"},
                {"uri": "x", "commit": "1234", "tag": "v1"},
                {"uri": "x", "commit": "1234", "branch": "x"},
                {"uri": "x", "tag": "v1", "branch": "x"},
                {"uri": "x", "commit": "1234", "branch": "x"},
            ]
            for i in bad_configs:
                with self.assertRaises(ValidationError):
                    sp.determine_git_ref(GitCfnginPackageSourceDefinitionModel(**i))

            self.assertEqual(
                sp.determine_git_ref(
                    GitCfnginPackageSourceDefinitionModel(
                        uri="https://github.com/remind101/stacker.git",
                        branch="release-1.0",
                    )
                ),
                "857b4834980e582874d70feef77bb064b60762d1",
            )
            self.assertEqual(
                sp.determine_git_ref(
                    GitCfnginPackageSourceDefinitionModel(
                        **{"uri": "git@foo", "commit": "1234"}
                    )
                ),
                "1234",
            )
            self.assertEqual(
                sp.determine_git_ref(
                    GitCfnginPackageSourceDefinitionModel(
                        **{"uri": "git@foo", "tag": "v1.0.0"}
                    )
                ),
                "v1.0.0",
            )


class MockException1(Exception):
    """Mock exception 1."""


class MockException(Exception):
    """Mock exception 2."""


class TestExceptionRetries(unittest.TestCase):
    """Test exception retries."""

    def setUp(self) -> None:
        """Run before tests."""
        self.counter = 0

    def _works_immediately(
        self, a: Any, b: Any, x: Any = None, y: Any = None
    ) -> List[Any]:
        """Works immediately."""
        self.counter += 1
        return [a, b, x, y]

    def _works_second_attempt(
        self, a: Any, b: Any, x: Any = None, y: Any = None
    ) -> List[Any]:
        """Works second_attempt."""
        self.counter += 1
        if self.counter == 2:
            return [a, b, x, y]
        raise Exception("Broke.")

    def _second_raises_exception2(
        self, a: Any, b: Any, x: Any = None, y: Any = None
    ) -> List[Any]:
        """Second raises exception2."""
        self.counter += 1
        if self.counter == 2:
            return [a, b, x, y]
        raise MockException("Broke.")

    def _throws_exception2(
        self, a: Any, b: Any, x: Any = None, y: Any = None
    ) -> List[Any]:
        """Throws exception2."""
        self.counter += 1
        raise MockException("Broke.")
