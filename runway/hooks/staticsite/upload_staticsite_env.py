"""CFNgin hook for uploading environment files to a static website S3 bucket."""
import logging
import json
import os
import yaml

LOGGER = logging.getLogger(__name__)


def sync(context, bucket, **kwargs):
    """Sync static website environment files to S3 bucket.

    Keyword Args:

        context (:class:`runway.cfngin.context.Context`): The context
            instance.
        provider (:class:`runway.cfngin.providers.base.BaseProvider`):
            The provider instance.
        bucket (str): The static site bucket name.
        files (List[Dict[str, str]]): List of files and file content that
            should be uploaded.

    """
    files = kwargs.get('files', [])

    LOGGER.debug('bucket: %s', bucket)
    LOGGER.debug('files: %s', json.dumps(files))

    session = context.get_session()
    s3_client = session.client('s3')

    for env_file in files:
        filename = env_file.get('name')
        LOGGER.debug('name: %s', filename)

        if 'content' in env_file:
            content = env_file.get('content')
            content_type = 'text/plain'

            _, ext = os.path.splitext(filename)
            LOGGER.debug('ext: %s', ext)

            if ext == '.json':
                content = json.dumps(content)
                content_type = 'application/json'
            elif ext in ['.yml', '.yaml']:
                content = yaml.dump(content)
                content_type = 'text/yaml'
            else:
                LOGGER.debug('type: %s', type(content))
                content = str(content)

            if content is not None:
                LOGGER.info(
                    'Uploading environment file as %s with content: %s', filename, content)

                s3_client.put_object(
                    Bucket=bucket,
                    Key=filename,
                    Body=content,
                    ContentType=content_type
                )
        elif 'ref' in env_file:
            ref = env_file.get('ref')

            LOGGER.info('Uploading environment file %s as %s ', ref, filename)

            s3_client.upload_file(ref, bucket, filename)

    return True
