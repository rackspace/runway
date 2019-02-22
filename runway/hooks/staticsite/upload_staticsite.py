"""Stacker hook for syncing static website to S3 bucket."""

import logging
import os
import time

from operator import itemgetter

from awscli.clidriver import create_clidriver

from stacker.lookups.handlers.output import OutputLookup
from stacker.session_cache import get_session

LOGGER = logging.getLogger(__name__)


def aws_cli(*cmd):
    """Invoke aws command."""
    old_env = dict(os.environ)
    try:

        # Environment
        env = os.environ.copy()
        env['LC_CTYPE'] = u'en_US.UTF'
        os.environ.update(env)

        # Run awscli in the same process
        exit_code = create_clidriver().main(*cmd)

        # Deal with problems
        if exit_code > 0:
            raise RuntimeError('AWS CLI exited with code {}'.format(exit_code))
    finally:
        os.environ.clear()
        os.environ.update(old_env)


def get_archives_to_prune(archives, hook_data):
    """Return list of keys to delete."""
    files_to_skip = []
    for i in ['current_archive_filename', 'old_archive_filename']:
        if hook_data.get(i):
            files_to_skip.append(hook_data[i])
    archives.sort(key=itemgetter('LastModified'),
                  reverse=False)  # sort from oldest to newest
    # Drop all but last 15 files
    return [i['Key'] for i in archives[:-15] if i['Key'] not in files_to_skip]


def sync(context, provider, **kwargs):  # pylint: disable=too-many-locals
    """Sync static website to S3 bucket."""
    session = get_session(provider.region)
    bucket_name = OutputLookup.handle(kwargs.get('bucket_output_lookup'),
                                      provider=provider,
                                      context=context)

    if context.hook_data['staticsite']['deploy_is_current']:
        LOGGER.info('staticsite: skipping upload; latest version already '
                    'deployed')
    else:
        distribution_id = OutputLookup.handle(
            kwargs.get('distributionid_output_lookup'),
            provider=provider,
            context=context
        )
        distribution_domain = OutputLookup.handle(
            kwargs.get('distributiondomain_output_lookup'),
            provider=provider,
            context=context
        )

        # Using the awscli for s3 syncing is incredibly suboptimal, but on
        # balance it's probably the most stable/efficient option for syncing
        # the files until https://github.com/boto/boto3/issues/358 is resolved
        aws_cli(['s3',
                 'sync',
                 context.hook_data['staticsite']['app_directory'],
                 "s3://%s/" % bucket_name,
                 '--delete'])

        cf_client = session.client('cloudfront')
        cf_client.create_invalidation(
            DistributionId=distribution_id,
            InvalidationBatch={'Paths': {'Quantity': 1, 'Items': ['/*']},
                               'CallerReference': str(time.time())}
        )
        LOGGER.info("staticsite: sync & CF invalidation of %s (domain %s) "
                    "complete",
                    distribution_id,
                    distribution_domain)

        if not context.hook_data['staticsite'].get('hash_tracking_disabled'):
            LOGGER.info("staticsite: updating environment SSM parameter %s "
                        "with hash %s",
                        context.hook_data['staticsite']['hash_tracking_parameter'],  # noqa
                        context.hook_data['staticsite']['hash'])
            ssm_client = session.client('ssm')
            ssm_client.put_parameter(
                Name=context.hook_data['staticsite']['hash_tracking_parameter'],  # noqa
                Description='Hash of currently deployed static website source',
                Value=context.hook_data['staticsite']['hash'],
                Type='String',
                Overwrite=True
            )
    LOGGER.info("staticsite: cleaning up old site archives...")
    archives = []
    s3_client = session.client('s3')
    list_objects_v2_paginator = s3_client.get_paginator('list_objects_v2')
    response_iterator = list_objects_v2_paginator.paginate(
        Bucket=context.hook_data['staticsite']['artifact_bucket_name'],
        Prefix=context.hook_data['staticsite']['artifact_key_prefix']
    )
    for page in response_iterator:
        archives.extend(page.get('Contents', []))
    archives_to_prune = get_archives_to_prune(
        archives,
        context.hook_data['staticsite']
    )
    # Iterate in chunks of 1000 to match delete_objects limit
    for objects in [archives_to_prune[i:i + 1000]
                    for i in range(0, len(archives_to_prune), 1000)]:
        s3_client.delete_objects(
            Bucket=context.hook_data['staticsite']['artifact_bucket_name'],
            Delete={'Objects': [{'Key': i} for i in objects]}
        )
    return True
