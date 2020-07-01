"""Test runway.hooks.staticsite.upload_staticsite."""
# pylint: disable=no-self-use,unused-import

import json
import yaml

import pytest
from mock import MagicMock
from botocore.stub import ANY

from runway.hooks.staticsite.upload_staticsite import auto_detect_content_type, sync_extra_files


class TestAutoDetectContentType(object):
    """Test runway.hooks.staticsite.upload_staticsite.auto_detect_content_type."""

    def test_json(self):
        """Test .json file names return application/json."""
        assert auto_detect_content_type('test.json') == 'application/json'

    def test_yml(self):
        """Test .yml file names return text/yaml."""
        assert auto_detect_content_type('test.yml') == 'text/yaml'

    def test_yaml(self):
        """Test .yaml file names return text/yaml."""
        assert auto_detect_content_type('test.yaml') == 'text/yaml'

    def test_default_content_type(self):
        """Test that None is returned by default."""
        assert auto_detect_content_type('test.txt') is None

    def test_no_extension(self):
        """Test filenames without an extention returns None."""
        assert auto_detect_content_type('test') is None


class TestSyncExtraFiles(object):
    """Test runway.hooks.staticsite.upload_staticsite.sync_extra_files."""

    def test_json_content(self, cfngin_context):
        """Test json content is put in s3."""
        s3_stub = cfngin_context.add_stubber('s3')

        content = {'a': 0}

        s3_stub.add_response('put_object', {}, {
            'Bucket': 'bucket',
            'Key': 'test.json',
            'Body': json.dumps(content),
            'ContentType': 'application/json'
        })

        files = [
            {'name': 'test.json', 'content': content}
        ]

        with s3_stub as stub:
            sync_extra_files(cfngin_context, MagicMock(), 'bucket', files=files, cf_disabled=True)
            stub.assert_no_pending_responses()

    def test_yaml_content(self, cfngin_context):
        """Test yaml content is put in s3."""
        s3_stub = cfngin_context.add_stubber('s3')

        content = {'a': 0}

        s3_stub.add_response('put_object', {}, {
            'Bucket': 'bucket',
            'Key': 'test.yaml',
            'Body': yaml.safe_dump(content),
            'ContentType': 'text/yaml'
        })

        files = [
            {'name': 'test.yaml', 'content': content}
        ]

        with s3_stub as stub:
            sync_extra_files(cfngin_context, MagicMock(), 'bucket', files=files, cf_disabled=True)
            stub.assert_no_pending_responses()

    def test_empty_content(self, cfngin_context):
        """Test empty content is not uploaded."""
        s3_stub = cfngin_context.add_stubber('s3')

        files = [
            {'name': 'test.yaml', 'content': {}}
        ]

        with s3_stub as stub:
            sync_extra_files(cfngin_context, MagicMock(), 'bucket', files=files, cf_disabled=True)
            stub.assert_no_pending_responses()

    def test_unknown_content_type(self, cfngin_context):
        """Test content w/out content_type."""
        s3_stub = cfngin_context.add_stubber('s3')

        files = [
            {'name': 'test', 'content': {'a': 0}}
        ]

        with s3_stub:
            with pytest.raises(ValueError):
                sync_extra_files(cfngin_context, MagicMock(), 'bucket', files=files, cf_disabled=True)

    def test_unsupported_content_type(self, cfngin_context):
        """Test content w/unsupported content."""
        s3_stub = cfngin_context.add_stubber('s3')

        files = [
            {'name': 'test', 'content': 123}
        ]

        with s3_stub:
            with pytest.raises(TypeError):
                sync_extra_files(cfngin_context, MagicMock(), 'bucket', files=files, cf_disabled=True)

    def test_file_reference(self, cfngin_context):
        """Test file is uploaded."""
        s3_stub = cfngin_context.add_stubber('s3')

        # This isn't ideal, but needed to get the correct stubbing.
        # Stubber doesn't support 'upload_file' so we need to assume it delegates to 'put_object'.
        # https://stackoverflow.com/questions/59303423/s3-boto3-stubber-doesnt-have-mapping-for-download-file
        s3_stub.add_response('put_object', {}, {
            'Bucket': 'bucket',
            'Key': 'test',
            'Body': ANY  # Don't want to make any more assumputions about how upload_file works
        })

        files = [
            {'name': 'test', 'file': 'Pipfile'}
        ]

        with s3_stub as stub:
            sync_extra_files(cfngin_context, MagicMock(), 'bucket', files=files, cf_disabled=True)
            stub.assert_no_pending_responses()

    def test_file_reference_with_content_type(self, cfngin_context):
        """Test file is uploaded with the content type."""
        s3_stub = cfngin_context.add_stubber('s3')

        s3_stub.add_response('put_object', {}, {
            'Bucket': 'bucket',
            'Key': 'test.json',
            'Body': ANY,
            'ContentType': 'application/json'
        })

        files = [
            {'name': 'test.json', 'file': 'Pipfile'}
        ]

        with s3_stub as stub:
            sync_extra_files(cfngin_context, MagicMock(), 'bucket', files=files, cf_disabled=True)
            stub.assert_no_pending_responses()
