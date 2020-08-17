"""CFNgin hook for cleaning up resources prior to CFN stack deletion."""
# TODO move to runway.cfngin.hooks on next major release
import logging

from botocore.exceptions import ClientError

from ..cfngin.lookups.handlers.output import OutputLookup
from ..cfngin.lookups.handlers.rxref import RxrefLookup
from ..cfngin.lookups.handlers.xref import XrefLookup

LOGGER = logging.getLogger(__name__)


def purge_bucket(context, provider, **kwargs):
    """Delete objects in bucket."""
    session = context.get_session()

    if kwargs.get("bucket_name"):
        bucket_name = kwargs["bucket_name"]
    else:
        if kwargs.get("bucket_output_lookup"):
            value = kwargs["bucket_output_lookup"]
            handler = OutputLookup.handle
        elif kwargs.get("bucket_rxref_lookup"):
            value = kwargs["bucket_rxref_lookup"]
            handler = RxrefLookup.handle
        elif kwargs.get("bucket_xref_lookup"):
            value = kwargs["bucket_xref_lookup"]
            handler = XrefLookup.handle
        else:
            LOGGER.error("bucket_name required but not defined")
            return False

        stack_name = context.get_fqn(value.split("::")[0])
        try:  # Exit early if the bucket's stack is already deleted
            session.client("cloudformation").describe_stacks(StackName=stack_name)
        except ClientError as exc:
            if "does not exist" in exc.response["Error"]["Message"]:
                LOGGER.info(
                    'stack "%s" does not exist; unable to resolve bucket name',
                    stack_name,
                )
                return True
            raise

        bucket_name = handler(value, provider=provider, context=context)

    s3_resource = session.resource("s3")
    try:
        s3_resource.meta.client.head_bucket(Bucket=bucket_name)
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "404":
            LOGGER.info(
                'bucket "%s" does not exist; unable to complete purge', bucket_name
            )
            return True
        raise

    bucket = s3_resource.Bucket(bucket_name)
    bucket.object_versions.delete()
    return True
