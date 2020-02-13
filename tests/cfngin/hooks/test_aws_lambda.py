"""Tests for runway.cfngin.hooks.aws_lambda."""
import os
import os.path
import random
import unittest
from io import BytesIO as StringIO
from zipfile import ZipFile

import boto3
import botocore
import mock
from moto import mock_s3
from testfixtures import ShouldRaise, TempDirectory, compare
from troposphere.awslambda import Code

from runway.cfngin.config import Config
from runway.cfngin.context import Context
from runway.cfngin.hooks.aws_lambda import (ZIP_PERMS_MASK, _calculate_hash,
                                            select_bucket_region,
                                            upload_lambda_functions)

from ..factories import mock_provider

REGION = "us-east-1"
ALL_FILES = (
    'f1/f1.py',
    'f1/f1.pyc',
    'f1/__init__.py',
    'f1/test/__init__.py',
    'f1/test/f1.py',
    'f1/test/f1.pyc',
    'f1/test2/test.txt',
    'f2/f2.js'
)
F1_FILES = [p[3:] for p in ALL_FILES if p.startswith('f1')]
F2_FILES = [p[3:] for p in ALL_FILES if p.startswith('f2')]


class TestLambdaHooks(unittest.TestCase):
    """Tests for runway.cfngin.hooks.aws_lambda."""

    _s3 = None

    @classmethod
    def temp_directory_with_files(cls, files=ALL_FILES):
        """Create a temp directory with files."""
        temp_dict = TempDirectory()
        for file_ in files:
            temp_dict.write(file_, b'')
        return temp_dict

    @property
    def s3(self):  # pylint: disable=invalid-name
        """Return S3 client."""
        if not self._s3:
            self._s3 = boto3.client('s3', region_name=REGION)
        return self._s3

    def assert_s3_zip_file_list(self, bucket, key, files):
        """Assert s3 zip file list."""
        object_info = self.s3.get_object(Bucket=bucket, Key=key)
        zip_data = StringIO(object_info['Body'].read())

        found_files = set()
        with ZipFile(zip_data, 'r') as zip_file:
            for zip_info in zip_file.infolist():
                perms = (zip_info.external_attr & ZIP_PERMS_MASK) >> 16
                self.assertIn(perms, (0o755, 0o644),
                              'ZIP member permission must be 755 or 644')
                found_files.add(zip_info.filename)

        compare(found_files, set(files))

    def assert_s3_bucket(self, bucket, present=True):
        """Assert s3 bucket."""
        try:
            self.s3.head_bucket(Bucket=bucket)
            if not present:
                self.fail('s3: bucket {} should not exist'.format(bucket))
        except botocore.exceptions.ClientError as err:
            if err.response['Error']['Code'] == '404':
                if present:
                    self.fail('s3: bucket {} does not exist'.format(bucket))

    def setUp(self):
        """Run before tests."""
        self.context = Context(
            config=Config({'namespace': 'test', 'stacker_bucket': 'test'}))
        self.provider = mock_provider(region="us-east-1")

    def run_hook(self, **kwargs):
        """Run hook."""
        real_kwargs = {
            'context': self.context,
            'provider': self.provider,
        }
        real_kwargs.update(kwargs)

        return upload_lambda_functions(**real_kwargs)

    @mock_s3
    def test_bucket_default(self):
        """Test bucket default."""
        self.assertIsNotNone(
            self.run_hook(functions={}))

        self.assert_s3_bucket('test')

    @mock_s3
    def test_bucket_custom(self):
        """Test bucket custom."""
        self.assertIsNotNone(
            self.run_hook(bucket='custom', functions={}))

        self.assert_s3_bucket('test', present=False)
        self.assert_s3_bucket('custom')

    @mock_s3
    def test_prefix(self):
        """Test prefix."""
        with self.temp_directory_with_files() as temp_dir:
            results = self.run_hook(prefix='cloudformation-custom-resources/',
                                    functions={
                                        'MyFunction': {
                                            'path': temp_dir.path + '/f1'
                                        }
                                    })

        self.assertIsNotNone(results)

        code = results.get('MyFunction')
        self.assertIsInstance(code, Code)
        self.assert_s3_zip_file_list(code.S3Bucket, code.S3Key, F1_FILES)
        self.assertTrue(code.S3Key.startswith(
            'cloudformation-custom-resources/lambda-MyFunction-'))

    @mock_s3
    def test_prefix_missing(self):
        """Test prefix missing."""
        with self.temp_directory_with_files() as temp_dir:
            results = self.run_hook(functions={
                'MyFunction': {
                    'path': temp_dir.path + '/f1'
                }
            })

        self.assertIsNotNone(results)

        code = results.get('MyFunction')
        self.assertIsInstance(code, Code)
        self.assert_s3_zip_file_list(code.S3Bucket, code.S3Key, F1_FILES)
        self.assertTrue(code.S3Key.startswith('lambda-MyFunction-'))

    @mock_s3
    def test_path_missing(self):
        """Test path missing."""
        msg = "missing required property 'path' in function 'MyFunction'"
        with ShouldRaise(ValueError(msg)):
            self.run_hook(functions={
                'MyFunction': {
                }
            })

    @mock_s3
    def test_path_relative(self):
        """Test path relative."""
        get_config_directory = 'runway.cfngin.hooks.aws_lambda.get_config_directory'
        with self.temp_directory_with_files(['test/test.py']) as temp_dir, \
                mock.patch(get_config_directory) as mock1:
            mock1.return_value = temp_dir.path

            results = self.run_hook(functions={
                'MyFunction': {
                    'path': 'test'
                }
            })

        self.assertIsNotNone(results)

        code = results.get('MyFunction')
        self.assertIsInstance(code, Code)
        self.assert_s3_zip_file_list(code.S3Bucket, code.S3Key, ['test.py'])

    @mock_s3
    def test_path_home_relative(self):
        """Test path home relative."""
        test_path = '~/test'

        orig_expanduser = os.path.expanduser
        with self.temp_directory_with_files(['test.py']) as temp_dir, \
                mock.patch('os.path.expanduser') as mock1:
            mock1.side_effect = lambda p: (temp_dir.path if p == test_path
                                           else orig_expanduser(p))

            results = self.run_hook(functions={
                'MyFunction': {
                    'path': test_path
                }
            })

        self.assertIsNotNone(results)

        code = results.get('MyFunction')
        self.assertIsInstance(code, Code)
        self.assert_s3_zip_file_list(code.S3Bucket, code.S3Key, ['test.py'])

    @mock_s3
    def test_multiple_functions(self):
        """Test multiple functions."""
        with self.temp_directory_with_files() as temp_dir:
            results = self.run_hook(functions={
                'MyFunction': {
                    'path': temp_dir.path + '/f1'
                },
                'OtherFunction': {
                    'path': temp_dir.path + '/f2'
                }
            })

        self.assertIsNotNone(results)

        f1_code = results.get('MyFunction')
        self.assertIsInstance(f1_code, Code)
        self.assert_s3_zip_file_list(f1_code.S3Bucket, f1_code.S3Key, F1_FILES)

        f2_code = results.get('OtherFunction')
        self.assertIsInstance(f2_code, Code)
        self.assert_s3_zip_file_list(f2_code.S3Bucket, f2_code.S3Key, F2_FILES)

    @mock_s3
    def test_patterns_invalid(self):
        """Test patterns invalid."""
        msg = ("Invalid file patterns in key 'include': must be a string or "
               'list of strings')

        with ShouldRaise(ValueError(msg)):
            self.run_hook(functions={
                'MyFunction': {
                    'path': 'test',
                    'include': {'invalid': 'invalid'}
                }
            })

    @mock_s3
    def test_patterns_include(self):
        """Test patterns include."""
        with self.temp_directory_with_files() as temp_dir:
            results = self.run_hook(functions={
                'MyFunction': {
                    'path': temp_dir.path + '/f1',
                    'include': ['*.py', 'test2/']
                }
            })

        self.assertIsNotNone(results)

        code = results.get('MyFunction')
        self.assertIsInstance(code, Code)
        self.assert_s3_zip_file_list(code.S3Bucket, code.S3Key, [
            'f1.py',
            '__init__.py',
            'test/__init__.py',
            'test/f1.py',
            'test2/test.txt'
        ])

    @mock_s3
    def test_patterns_exclude(self):
        """Test patterns exclude."""
        with self.temp_directory_with_files() as temp_dir:
            results = self.run_hook(functions={
                'MyFunction': {
                    'path': temp_dir.path + '/f1',
                    'exclude': ['*.pyc', 'test/']
                }
            })

        self.assertIsNotNone(results)

        code = results.get('MyFunction')
        self.assertIsInstance(code, Code)
        self.assert_s3_zip_file_list(code.S3Bucket, code.S3Key, [
            'f1.py',
            '__init__.py',
            'test2/test.txt'
        ])

    @mock_s3
    def test_patterns_include_exclude(self):
        """Test patterns include exclude."""
        with self.temp_directory_with_files() as temp_dir:
            results = self.run_hook(functions={
                'MyFunction': {
                    'path': temp_dir.path + '/f1',
                    'include': '*.py',
                    'exclude': 'test/'
                }
            })

        self.assertIsNotNone(results)

        code = results.get('MyFunction')
        self.assertIsInstance(code, Code)
        self.assert_s3_zip_file_list(code.S3Bucket, code.S3Key, [
            'f1.py',
            '__init__.py'
        ])

    @mock_s3
    def test_patterns_exclude_all(self):
        """Test patterns exclude all."""
        msg = ('Empty list of files for Lambda payload. Check your '
               'include/exclude options for errors.')

        with self.temp_directory_with_files() as temp_dir, \
                ShouldRaise(RuntimeError(msg)):

            results = self.run_hook(functions={
                'MyFunction': {
                    'path': temp_dir.path + '/f1',
                    'exclude': ['**']
                }
            })

            self.assertIsNone(results)

    @mock_s3
    def test_idempotence(self):
        """Test idempotence."""
        bucket_name = 'test'

        with self.temp_directory_with_files() as temp_dir:
            functions = {
                'MyFunction': {
                    'path': temp_dir.path + '/f1'
                }
            }

            self.s3.create_bucket(Bucket=bucket_name)

            previous = None
            for _ in range(2):
                results = self.run_hook(bucket=bucket_name,
                                        functions=functions)
                self.assertIsNotNone(results)

                code = results.get('MyFunction')
                self.assertIsInstance(code, Code)

                if not previous:
                    previous = code.S3Key
                    continue

                compare(previous, code.S3Key,
                        prefix="zipfile name should not be modified in "
                               "repeated runs.")

    def test_calculate_hash(self):
        """Test calculate hash."""
        with self.temp_directory_with_files() as temp_dir1:
            root = temp_dir1.path
            hash1 = _calculate_hash(ALL_FILES, root)

        with self.temp_directory_with_files() as temp_dir2:
            root = temp_dir2.path
            hash2 = _calculate_hash(ALL_FILES, root)

        with self.temp_directory_with_files() as temp_dir3:
            root = temp_dir3.path
            with open(os.path.join(root, ALL_FILES[0]), "w") as _file:
                _file.write("modified file data")
            hash3 = _calculate_hash(ALL_FILES, root)

        self.assertEqual(hash1, hash2)
        self.assertNotEqual(hash1, hash3)
        self.assertNotEqual(hash2, hash3)

    def test_calculate_hash_diff_filename_same_contents(self):
        """Test calculate hash diff filename same contents."""
        files = ["file1.txt", "f2/file2.txt"]
        file1, file2 = files
        with TempDirectory() as temp_dir:
            root = temp_dir.path
            for file_name in files:
                temp_dir.write(file_name, b"data")
            hash1 = _calculate_hash([file1], root)
            hash2 = _calculate_hash([file2], root)
        self.assertNotEqual(hash1, hash2)

    def test_calculate_hash_different_ordering(self):
        """Test calculate hash different ordering."""
        files1 = ALL_FILES
        files2 = random.sample(ALL_FILES, k=len(ALL_FILES))
        with TempDirectory() as temp_dir1:
            root1 = temp_dir1.path
            for file_name in files1:
                temp_dir1.write(file_name, b"")
            with TempDirectory() as temp_dir2:
                root2 = temp_dir2.path
                for file_name in files2:
                    temp_dir2.write(file_name, b"")
                hash1 = _calculate_hash(files1, root1)
                hash2 = _calculate_hash(files2, root2)
                self.assertEqual(hash1, hash2)

    def test_select_bucket_region(self):
        """Test select bucket region."""
        tests = (
            (("myBucket", "us-east-1", "us-west-1", "eu-west-1"), "us-east-1"),
            (("myBucket", None, "us-west-1", "eu-west-1"), "eu-west-1"),
            ((None, "us-east-1", "us-west-1", "eu-west-1"), "us-west-1"),
            ((None, "us-east-1", None, "eu-west-1"), "eu-west-1"),

        )

        for args, result in tests:
            self.assertEqual(select_bucket_region(*args), result)

    @mock_s3
    def test_follow_symlink_nonbool(self):
        """Test follow symlink nonbool."""
        msg = "follow_symlinks option must be a boolean"
        with ShouldRaise(ValueError(msg)):
            self.run_hook(follow_symlinks="raiseValueError", functions={
                'MyFunction': {
                }
            })

    @mock_s3
    def test_follow_symlink_true(self):
        """Testing if symlinks are followed."""
        with self.temp_directory_with_files() as temp_dir1:
            root1 = temp_dir1.path
            with self.temp_directory_with_files() as temp_dir2:
                root2 = temp_dir2.path
                os.symlink(root1 + "/f1", root2 + "/f3")
                results = self.run_hook(follow_symlinks=True, functions={
                    'MyFunction': {
                        'path': root2}
                })
            self.assertIsNotNone(results)

            code = results.get('MyFunction')
            self.assertIsInstance(code, Code)
            self.assert_s3_zip_file_list(code.S3Bucket, code.S3Key, [
                'f1/f1.py',
                'f1/__init__.py',
                'f1/f1.pyc',
                'f1/test/__init__.py',
                'f1/test/f1.py',
                'f1/test/f1.pyc',
                'f1/test2/test.txt',
                'f2/f2.js',
                'f3/__init__.py',
                'f3/f1.py',
                'f3/f1.pyc',
                'f3/test/__init__.py',
                'f3/test/f1.py',
                'f3/test/f1.pyc',
                'f3/test2/test.txt'
            ])

    @mock_s3
    def test_follow_symlink_false(self):
        """Testing if syminks are present and not followed."""
        with self.temp_directory_with_files() as temp_dir1:
            root1 = temp_dir1.path
            with self.temp_directory_with_files() as temp_dir2:
                root2 = temp_dir2.path
                os.symlink(root1 + "/f1", root2 + "/f3")
                results = self.run_hook(follow_symlinks=False, functions={
                    'MyFunction': {
                        'path': root2}
                })
            self.assertIsNotNone(results)

            code = results.get('MyFunction')
            self.assertIsInstance(code, Code)
            self.assert_s3_zip_file_list(code.S3Bucket, code.S3Key, [
                'f1/f1.py',
                'f1/__init__.py',
                'f1/f1.pyc',
                'f1/test/__init__.py',
                'f1/test/f1.py',
                'f1/test/f1.pyc',
                'f1/test2/test.txt',
                'f2/f2.js'
            ])

    @mock_s3
    def test_follow_symlink_omitted(self):
        """Same as test_follow_symlink_false, but default behavior."""
        with self.temp_directory_with_files() as temp_dir1:
            root1 = temp_dir1.path
            with self.temp_directory_with_files() as temp_dir2:
                root2 = temp_dir2.path
                os.symlink(root1 + "/f1", root2 + "/f3")
                results = self.run_hook(functions={
                    'MyFunction': {
                        'path': root2}
                })
            self.assertIsNotNone(results)

            code = results.get('MyFunction')
            self.assertIsInstance(code, Code)
            self.assert_s3_zip_file_list(code.S3Bucket, code.S3Key, [
                'f1/f1.py',
                'f1/__init__.py',
                'f1/f1.pyc',
                'f1/test/__init__.py',
                'f1/test/f1.py',
                'f1/test/f1.pyc',
                'f1/test2/test.txt',
                'f2/f2.js',
            ])
