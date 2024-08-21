"""CFNgin lookup registry."""

from __future__ import annotations

import logging
from typing import Any, cast

from ...lookups.handlers.base import LookupHandler
from ...lookups.handlers.cfn import CfnLookup
from ...lookups.handlers.ecr import EcrLookup
from ...lookups.handlers.env import EnvLookup
from ...lookups.handlers.random_string import RandomStringLookup
from ...lookups.handlers.ssm import SsmLookup
from ...utils import DOC_SITE, load_object_from_string
from .handlers.ami import AmiLookup
from .handlers.awslambda import AwsLambdaLookup
from .handlers.default import DefaultLookup
from .handlers.dynamodb import DynamodbLookup
from .handlers.envvar import EnvvarLookup
from .handlers.file import FileLookup
from .handlers.hook_data import HookDataLookup
from .handlers.kms import KmsLookup
from .handlers.output import OutputLookup
from .handlers.rxref import RxrefLookup
from .handlers.split import SplitLookup
from .handlers.xref import XrefLookup

CFNGIN_LOOKUP_HANDLERS: dict[str, type[LookupHandler[Any]]] = {}
LOGGER = logging.getLogger(__name__)


def register_lookup_handler(
    lookup_type: str, handler_or_path: str | type[LookupHandler[Any]]
) -> None:
    """Register a lookup handler.

    Args:
        lookup_type: Name to register the handler under.
        handler_or_path: A function or a path to a handler.

    """
    handler = handler_or_path
    LOGGER.debug("registering CFNgin lookup: %s=%s", lookup_type, handler_or_path)

    if isinstance(handler_or_path, str):
        handler = cast(type, load_object_from_string(handler_or_path))
    else:
        handler = handler_or_path

    try:
        if issubclass(handler, LookupHandler):
            CFNGIN_LOOKUP_HANDLERS[lookup_type] = handler
            return
    # Handler is a not a new-style handler
    except Exception:  # noqa: BLE001
        LOGGER.debug("failed to validate lookup handler", exc_info=True)
    LOGGER.error(
        'lookup "%s" uses an unsupported format; to learn how to write '
        "lookups visit %s/page/cfngin/lookups/index.html#writing-a-custom-lookup",
        lookup_type,
        DOC_SITE,
    )
    raise TypeError(
        f"lookup {handler_or_path} must be a subclass of "
        "runway.lookups.handlers.base.LookupHandler"
    )


def unregister_lookup_handler(lookup_type: str) -> None:
    """Unregister the specified lookup type.

    This is useful when testing various lookup types if you want to unregister
    the lookup type after the test runs.

    Args:
        lookup_type: Name of the lookup type to unregister.

    """
    CFNGIN_LOOKUP_HANDLERS.pop(lookup_type, None)


register_lookup_handler(AmiLookup.TYPE_NAME, AmiLookup)
register_lookup_handler(AwsLambdaLookup.TYPE_NAME, AwsLambdaLookup)
register_lookup_handler(AwsLambdaLookup.Code.TYPE_NAME, AwsLambdaLookup.Code)
register_lookup_handler(AwsLambdaLookup.CodeSha256.TYPE_NAME, AwsLambdaLookup.CodeSha256)
register_lookup_handler(
    AwsLambdaLookup.CompatibleArchitectures.TYPE_NAME,
    AwsLambdaLookup.CompatibleArchitectures,
)
register_lookup_handler(
    AwsLambdaLookup.CompatibleRuntimes.TYPE_NAME, AwsLambdaLookup.CompatibleRuntimes
)
register_lookup_handler(AwsLambdaLookup.Content.TYPE_NAME, AwsLambdaLookup.Content)
register_lookup_handler(AwsLambdaLookup.LicenseInfo.TYPE_NAME, AwsLambdaLookup.LicenseInfo)
register_lookup_handler(AwsLambdaLookup.Runtime.TYPE_NAME, AwsLambdaLookup.Runtime)
register_lookup_handler(AwsLambdaLookup.S3Bucket.TYPE_NAME, AwsLambdaLookup.S3Bucket)
register_lookup_handler(AwsLambdaLookup.S3Key.TYPE_NAME, AwsLambdaLookup.S3Key)
register_lookup_handler(AwsLambdaLookup.S3ObjectVersion.TYPE_NAME, AwsLambdaLookup.S3ObjectVersion)
register_lookup_handler(CfnLookup.TYPE_NAME, CfnLookup)
register_lookup_handler(DefaultLookup.TYPE_NAME, DefaultLookup)
register_lookup_handler(DynamodbLookup.TYPE_NAME, DynamodbLookup)
register_lookup_handler(EcrLookup.TYPE_NAME, EcrLookup)
register_lookup_handler(EnvLookup.TYPE_NAME, EnvLookup)
register_lookup_handler(EnvvarLookup.TYPE_NAME, EnvvarLookup)
register_lookup_handler(FileLookup.TYPE_NAME, FileLookup)
register_lookup_handler(HookDataLookup.TYPE_NAME, HookDataLookup)
register_lookup_handler(KmsLookup.TYPE_NAME, KmsLookup)
register_lookup_handler(OutputLookup.TYPE_NAME, OutputLookup)
register_lookup_handler(RandomStringLookup.TYPE_NAME, RandomStringLookup)
register_lookup_handler(RxrefLookup.TYPE_NAME, RxrefLookup)
register_lookup_handler(SplitLookup.TYPE_NAME, SplitLookup)
register_lookup_handler(SsmLookup.TYPE_NAME, SsmLookup)
register_lookup_handler(XrefLookup.TYPE_NAME, XrefLookup)
