"""CFNgin hook for syncing static website to S3 bucket."""
# TODO move to runway.cfngin.hooks on next major release
import logging
import time
from operator import itemgetter

from ...cfngin.lookups.handlers.output import OutputLookup
from ...cfngin.session_cache import get_session
from ...commands.runway.run_aws import aws_cli

LOGGER = logging.getLogger(__name__)


def get_archives_to_prune(archives, hook_data):
    """Return list of keys to delete.

    Keyword Args:
        archives (Dict): The full list of file archives
        hook_data (Dict): CFNgin hook data

    """
    files_to_skip = []

    for i in ['current_archive_filename', 'old_archive_filename']:
        if hook_data.get(i):
            files_to_skip.append(hook_data[i])

    archives.sort(key=itemgetter('LastModified'), reverse=False)  # sort from oldest to newest

    # Drop all but last 15 files
    return [i['Key'] for i in archives[:-15] if i['Key'] not in files_to_skip]


def sync(context, provider, **kwargs):
    """Sync static website to S3 bucket.

    Keyword Args:

        context (:class:`runway.cfngin.context.Context`): The context
            instance.
        provider (:class:`runway.cfngin.providers.base.BaseProvider`):
            The provider instance.

    """
    session = get_session(provider.region)
    bucket_name = OutputLookup.handle(kwargs.get('bucket_output_lookup'),
                                      provider=provider,
                                      context=context)

    if context.hook_data['staticsite']['deploy_is_current']:
        LOGGER.info('staticsite: skipping upload; latest version already '
                    'deployed')
        if kwargs.get('cf_disabled', '') == 'true':
            display_static_website_url(kwargs.get('website_url'), provider, context)
    else:
        # Using the awscli for s3 syncing is incredibly suboptimal, but on
        # balance it's probably the most stable/efficient option for syncing
        # the files until https://github.com/boto/boto3/issues/358 is resolved
        aws_cli(['s3',
                 'sync',
                 context.hook_data['staticsite']['app_directory'],
                 "s3://%s/" % bucket_name,
                 '--delete'])

        if kwargs.get('cf_disabled', False):
            display_static_website_url(kwargs.get('website_url'), provider, context)
        else:
            distribution = get_distribution_data(context, provider, **kwargs)
            invalidate_distribution(session, **distribution)

        LOGGER.info("staticsite: sync " "complete")

        update_ssm_hash(context, session)

    prune_archives(context, session)
    return True


def display_static_website_url(website_url_handle, provider, context):
    """Based on the url handle display the static website url.

    Keyword Args:
        website_url_handle (str): the Output handle for the website url
        provider (:class:`runway.cfngin.providers.base.BaseProvider`):
            The provider instance.
        context (:class:`runway.cfngin.context.Context`): context instance

    """
    bucket_url = OutputLookup.handle(website_url_handle,
                                     provider=provider,
                                     context=context)
    LOGGER.info("STATIC WEBSITE URL: %s", bucket_url)


def update_ssm_hash(context, session):
    """Update the SSM hash with the new tracking data.

    Keyword Args:
        context (:class:`runway.cfngin.context.Context`): context instance
        session (:class:`runway.cfngin.session.Session`): CFNgin session

    """
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
    return True


def get_distribution_data(context, provider, **kwargs):
    """Retrieve information about the distribution.

    Keyword Args:
        context (:class:`runway.cfngin.context.Context`): The context
            instance.
        provider (:class:`runway.cfngin.providers.base.BaseProvider`):
            The provider instance

    """
    LOGGER.info("Retrieved distribution data")
    return {
        'identifier': OutputLookup.handle(
            kwargs.get('distributionid_output_lookup'),
            provider=provider,
            context=context
        ),
        'domain': OutputLookup.handle(
            kwargs.get('distributiondomain_output_lookup'),
            provider=provider,
            context=context
        ),
        'path': kwargs.get('distribution_path', '/*')
    }


def invalidate_distribution(session, identifier='', path='', domain='', **_):
    """Invalidate the current distribution.

    Keyword Args:
        session (Session): The current CFNgin session
        identifier (string): The distribution id
        path (string): The distribution path
        domain (string): The distribution domain

    """
    LOGGER.info("staticsite: Invalidating CF distribution")
    cf_client = session.client('cloudfront')
    cf_client.create_invalidation(
        DistributionId=identifier,
        InvalidationBatch={
            'Paths': {
                'Quantity': 1,
                'Items': [path]},
            'CallerReference': str(time.time())}
    )

    LOGGER.info("staticsite: CF invalidation of %s (domain %s) " "complete", identifier, domain)
    return True


def prune_archives(context, session):
    """Prune the archives from the bucket.

    Keyword Args:
        context (:class:`runway.cfngin.context.Context`): The context
            instance.
        session (:class:`runway.cfngin.session.Session`): The CFNgin
            session.

    """
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
