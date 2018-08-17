"""Stacker hook for syncing static website to S3 bucket."""

import logging
import os
import time

from awscli.clidriver import create_clidriver

from stacker.lookups.handlers.output import handler as output_handler
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


def sync(context, provider, **kwargs):
    """Sync static website to S3 bucket."""
    if context.hook_data['staticsite']['deploy_is_current']:
        LOGGER.info('staticsite: skipping upload; latest version already '
                    'deployed')
        return True

    bucket_name = output_handler(kwargs.get('bucket_output_lookup'),
                                 provider=provider,
                                 context=context)
    distribution_id = output_handler(
        kwargs.get('distributionid_output_lookup'),
        provider=provider,
        context=context
    )
    distribution_domain = output_handler(
        kwargs.get('distributiondomain_output_lookup'),
        provider=provider,
        context=context
    )

    # Using the awscli for s3 syncing is incredibly suboptimal, but on balance
    # it's probably the most stable/efficient option for syncing the files
    # until https://github.com/boto/boto3/issues/358 is resolved
    aws_cli(['s3',
             'sync',
             context.hook_data['staticsite']['app_directory'],
             "s3://%s/" % bucket_name,
             '--delete'])

    session = get_session(provider.region)
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
        LOGGER.info("staticsite: updating environment SSM parameter %s with "
                    "hash %s",
                    context.hook_data['staticsite']['hash_tracking_parameter'],
                    context.hook_data['staticsite']['hash'])
        ssm_client = session.client('ssm')
        ssm_client.put_parameter(
            Name=context.hook_data['staticsite']['hash_tracking_parameter'],
            Description='Hash of currently deployed static website source',
            Value=context.hook_data['staticsite']['hash'],
            Type='String',
            Overwrite=True
        )
    return True
