"""Stacker hook for cleaning up resources prior to CFN stack deletion."""

import logging

from botocore.exceptions import ClientError

from stacker.lookups.handlers import output as output_module
from stacker.lookups.handlers import rxref as rxref_module
from stacker.lookups.handlers import xref as xref_module
from stacker.session_cache import get_session

LOGGER = logging.getLogger(__name__)


def purge_bucket(context, provider, **kwargs):
    """Delete objects in bucket."""
    session = get_session(provider.region)

    if kwargs.get('bucket_name'):
        bucket_name = kwargs['bucket_name']
    else:
        if kwargs.get('bucket_output_lookup'):
            value = kwargs['bucket_output_lookup']
            handler = getattr(output_module, 'handler')
        elif kwargs.get('bucket_rxref_lookup'):
            value = kwargs['bucket_rxref_lookup']
            handler = getattr(rxref_module, 'handler')
        elif kwargs.get('bucket_xref_lookup'):
            value = kwargs['bucket_xref_lookup']
            handler = getattr(xref_module, 'handler')
        else:
            LOGGER.fatal('No bucket name/source provided.')
            return False

        try:  # Exit early if the bucket's stack is already deleted
            session.client('cloudformation').describe_stacks(
                StackName=context.get_fqn(value.split('::')[0])
            )
        except ClientError as exc:
            if 'does not exist' in exc.response['Error']['Message']:
                LOGGER.info('S3 bucket stack appears to have already been '
                            'deleted...')
                return True
            raise

    bucket_name = handler(
        value,
        provider=provider,
        context=context
    )

    s3_resource = session.resource('s3')
    try:
        s3_resource.meta.client.head_bucket(Bucket=bucket_name)
    except ClientError as exc:
        if exc.response['Error']['Code'] == '404':
            LOGGER.info("%s S3 bucket appears to have already been deleted...",
                        bucket_name)
            return True
        raise

    bucket = s3_resource.Bucket(bucket_name)
    bucket.object_versions.delete()
    return True
