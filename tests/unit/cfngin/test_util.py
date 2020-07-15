"""Tests for runway.cfngin.util."""
# pylint: disable=unused-argument,invalid-name
import unittest

import boto3
import mock

from runway.cfngin.config import GitPackageSource
from runway.cfngin.util import (Extractor, SourceProcessor, TarExtractor,
                                TarGzipExtractor, ZipExtractor, camel_to_snake,
                                cf_safe_name, get_client_region,
                                get_s3_endpoint, merge_map,
                                parse_cloudformation_template,
                                s3_bucket_location_constraint,
                                yaml_to_ordered_dict)

AWS_REGIONS = ["us-east-1", "cn-north-1", "ap-northeast-1", "eu-west-1",
               "ap-southeast-1", "ap-southeast-2", "us-west-2", "us-gov-west-1",
               "us-west-1", "eu-central-1", "sa-east-1"]


def mock_create_cache_directories(self, **kwargs):
    """Mock create cache directories.

    Don't actually need the directories created in testing

    """
    return 1


class TestUtil(unittest.TestCase):
    """Tests for runway.cfngin.util."""

    def test_cf_safe_name(self):
        """Test cf safe name."""
        tests = (
            ("abc-def", "AbcDef"),
            ("GhI", "GhI"),
            ("jKlm.noP", "JKlmNoP")
        )
        for test in tests:
            self.assertEqual(cf_safe_name(test[0]), test[1])

    def test_camel_to_snake(self):
        """Test camel to snake."""
        tests = (
            ("TestTemplate", "test_template"),
            ("testTemplate", "test_template"),
            ("test_Template", "test__template"),
            ("testtemplate", "testtemplate"),
        )
        for test in tests:
            self.assertEqual(camel_to_snake(test[0]), test[1])

    def test_merge_map(self):
        """Test merge map."""
        tests = [
            # 2 lists of stacks defined
            [{'stacks': [{'stack1': {'variables': {'a': 'b'}}}]},
             {'stacks': [{'stack2': {'variables': {'c': 'd'}}}]},
             {'stacks': [
                 {'stack1': {
                     'variables': {
                         'a': 'b'}}},
                 {'stack2': {
                     'variables': {
                         'c': 'd'}}}]}],
            # A list of stacks combined with a higher precedence dict of stacks
            [{'stacks': [{'stack1': {'variables': {'a': 'b'}}}]},
             {'stacks': {'stack2': {'variables': {'c': 'd'}}}},
             {'stacks': {'stack2': {'variables': {'c': 'd'}}}}],
            # 2 dicts of stacks with non-overlapping variables merged
            [{'stacks': {'stack1': {'variables': {'a': 'b'}}}},
             {'stacks': {'stack1': {'variables': {'c': 'd'}}}},
             {'stacks': {
                 'stack1': {
                     'variables': {
                         'a': 'b',
                         'c': 'd'}}}}],
            # 2 dicts of stacks with overlapping variables merged
            [{'stacks': {'stack1': {'variables': {'a': 'b'}}}},
             {'stacks': {'stack1': {'variables': {'a': 'c'}}}},
             {'stacks': {'stack1': {'variables': {'a': 'c'}}}}],
        ]
        for test in tests:
            self.assertEqual(merge_map(test[0], test[1]), test[2])

    def test_yaml_to_ordered_dict(self):
        """Test yaml to ordered dict."""
        raw_config = """
        pre_build:
          hook2:
            path: foo.bar
          hook1:
            path: foo1.bar1
        """
        config = yaml_to_ordered_dict(raw_config)
        self.assertEqual(list(config['pre_build'].keys())[0], 'hook2')
        self.assertEqual(config['pre_build']['hook2']['path'], 'foo.bar')

    def test_get_client_region(self):
        """Test get client region."""
        regions = ["us-east-1", "us-west-1", "eu-west-1", "sa-east-1"]
        for region in regions:
            client = boto3.client("s3", region_name=region)
            self.assertEqual(get_client_region(client), region)

    def test_get_s3_endpoint(self):
        """Test get s3 endpoint."""
        endpoint_url = "https://example.com"
        client = boto3.client("s3", region_name="us-east-1",
                              endpoint_url=endpoint_url)
        self.assertEqual(get_s3_endpoint(client), endpoint_url)

    def test_s3_bucket_location_constraint(self):
        """Test s3 bucket location constraint."""
        tests = (
            ("us-east-1", ""),
            ("us-west-1", "us-west-1")
        )
        for region, result in tests:
            self.assertEqual(
                s3_bucket_location_constraint(region),
                result
            )

    def test_parse_cloudformation_template(self):
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
            'AWSTemplateFormatVersion': '2010-09-09',
            'Outputs': {'DummyId': {'Value': 'dummy-1234'}},
            'Parameters': {'Param1': {'Type': 'String'}},
            'Resources': {
                'Bucket': {'Type': 'AWS::S3::Bucket',
                           'Properties': {
                               'BucketName': {
                                   u'Fn::Join': [
                                       '-',
                                       [{u'Ref': u'AWS::StackName'},
                                        {u'Ref': u'AWS::Region'}]
                                   ]
                               }
                           }}
            }
        }
        self.assertEqual(
            parse_cloudformation_template(template),
            parsed_template
        )

    def test_extractors(self):
        """Test extractors."""
        self.assertEqual(Extractor('test.zip').archive, 'test.zip')
        self.assertEqual(TarExtractor().extension(), '.tar')
        self.assertEqual(TarGzipExtractor().extension(), '.tar.gz')
        self.assertEqual(ZipExtractor().extension(), '.zip')
        for i in [TarExtractor(), ZipExtractor(), ZipExtractor()]:
            i.set_archive('/tmp/foo')
            self.assertEqual(i.archive.endswith(i.extension()), True)

    def test_SourceProcessor_helpers(self):  # noqa: N802
        """Test SourceProcessor helpers."""
        with mock.patch.object(SourceProcessor,
                               'create_cache_directories',
                               new=mock_create_cache_directories):
            sp = SourceProcessor(sources={})

            self.assertEqual(
                sp.sanitize_git_path('git@github.com:foo/bar.git'),
                'git_github.com_foo_bar'
            )
            self.assertEqual(
                sp.sanitize_uri_path('http://example.com/foo/bar.gz@1'),
                'http___example.com_foo_bar.gz_1'
            )
            self.assertEqual(
                sp.sanitize_git_path('git@github.com:foo/bar.git', 'v1'),
                'git_github.com_foo_bar-v1'
            )

            for i in [GitPackageSource({'branch': 'foo'}), {'branch': 'foo'}]:
                self.assertEqual(
                    sp.determine_git_ls_remote_ref(i),
                    'refs/heads/foo'
                )
            for i in [{'uri': 'git@foo'}, {'tag': 'foo'}, {'commit': '1234'}]:
                self.assertEqual(
                    sp.determine_git_ls_remote_ref(GitPackageSource(i)),
                    'HEAD'
                )
                self.assertEqual(
                    sp.determine_git_ls_remote_ref(i),
                    'HEAD'
                )

            self.assertEqual(
                sp.git_ls_remote('https://github.com/remind101/stacker.git',
                                 'refs/heads/release-1.0'),
                b'857b4834980e582874d70feef77bb064b60762d1'
            )

            bad_configs = [{'uri': 'x',
                            'commit': '1234',
                            'tag': 'v1',
                            'branch': 'x'},
                           {'uri': 'x', 'commit': '1234', 'tag': 'v1'},
                           {'uri': 'x', 'commit': '1234', 'branch': 'x'},
                           {'uri': 'x', 'tag': 'v1', 'branch': 'x'},
                           {'uri': 'x', 'commit': '1234', 'branch': 'x'}]
            for i in bad_configs:
                with self.assertRaises(ImportError):
                    sp.determine_git_ref(GitPackageSource(i))
                with self.assertRaises(ImportError):
                    sp.determine_git_ref(i)

            self.assertEqual(
                sp.determine_git_ref(
                    GitPackageSource({'uri': 'https://github.com/remind101/'
                                             'stacker.git',
                                      'branch': 'release-1.0'})),
                '857b4834980e582874d70feef77bb064b60762d1'
            )
            self.assertEqual(
                sp.determine_git_ref(
                    GitPackageSource({'uri': 'git@foo', 'commit': '1234'})),
                '1234'
            )
            self.assertEqual(
                sp.determine_git_ref({'uri': 'git@foo', 'commit': '1234'}),
                '1234'
            )
            self.assertEqual(
                sp.determine_git_ref(
                    GitPackageSource({'uri': 'git@foo', 'tag': 'v1.0.0'})),
                'v1.0.0'
            )
            self.assertEqual(
                sp.determine_git_ref({'uri': 'git@foo', 'tag': 'v1.0.0'}),
                'v1.0.0'
            )


class MockException1(Exception):
    """Mock exception 1."""


class MockException(Exception):
    """Mock exception 2."""


class TestExceptionRetries(unittest.TestCase):
    """Test exception retries."""

    def setUp(self):
        """Run before tests."""
        self.counter = 0

    def _works_immediately(self, a, b, x=None, y=None):
        """Works immediately."""
        self.counter += 1
        return [a, b, x, y]

    def _works_second_attempt(self, a, b, x=None, y=None):
        """Works second_attempt."""
        self.counter += 1
        if self.counter == 2:
            return [a, b, x, y]
        raise Exception("Broke.")

    def _second_raises_exception2(self, a, b, x=None, y=None):
        """Second raises exception2."""
        self.counter += 1
        if self.counter == 2:
            return [a, b, x, y]
        raise MockException("Broke.")

    def _throws_exception2(self, a, b, x=None, y=None):
        """Throws exception2."""
        self.counter += 1
        raise MockException("Broke.")
