"""CFNgin hook for syncing static website to S3 bucket."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from operator import itemgetter
from typing import TYPE_CHECKING, Any, cast

import yaml

from ....core.providers.aws.s3 import Bucket
from ....module.staticsite.options import RunwayStaticSiteExtraFileDataModel
from ....utils import JsonEncoder
from ..base import HookArgsBaseModel

if TYPE_CHECKING:
    from boto3.session import Session

    from ....context import CfnginContext

LOGGER = logging.getLogger(__name__)


class HookArgs(HookArgsBaseModel):
    """Hook arguments."""

    bucket_name: str
    """S3 bucket name."""

    cf_disabled: bool = False
    """Disable the use of CloudFront."""

    distribution_domain: str = "undefined"
    """Domain of the CloudFront distribution."""

    distribution_id: str = "undefined"
    """CloudFront distribution ID."""

    distribution_path: str = "/*"
    """Path in the CloudFront distribution to invalidate."""

    extra_files: list[RunwayStaticSiteExtraFileDataModel] = []
    """Extra files to sync to the S3 bucket."""

    website_url: str | None = None
    """S3 bucket website URL."""


def get_archives_to_prune(archives: list[dict[str, Any]], hook_data: dict[str, Any]) -> list[str]:
    """Return list of keys to delete.

    Args:
        archives: The full list of file archives
        hook_data: CFNgin hook data

    """
    files_to_skip = [
        hook_data[i]
        for i in ["current_archive_filename", "old_archive_filename"]
        if hook_data.get(i)
    ]

    archives.sort(key=itemgetter("LastModified"), reverse=False)  # sort from oldest to newest

    # Drop all but last 15 files
    return [i["Key"] for i in archives[:-15] if i["Key"] not in files_to_skip]


def sync(context: CfnginContext, *__args: Any, **kwargs: Any) -> bool:
    """Sync static website to S3 bucket.

    Arguments parsed by :class:`~runway.cfngin.hooks.staticsite.upload_staticsite.HookArgs`.

    Args:
        context: The context instance.
        **kwargs: Arbitrary keyword arguments.

    """
    args = HookArgs.model_validate(kwargs)
    session = context.get_session()
    build_context = context.hook_data["staticsite"]
    invalidate_cache = False

    synced_extra_files = sync_extra_files(
        context,
        args.bucket_name,
        args.extra_files,
        hash_tracking_parameter=build_context.get("hash_tracking_parameter"),
    )

    if synced_extra_files:
        invalidate_cache = True

    if build_context["deploy_is_current"]:
        LOGGER.info("skipped upload; latest version already deployed")
    else:
        bucket = Bucket(context, args.bucket_name)
        bucket.sync_from_local(
            build_context["app_directory"],
            delete=True,
            exclude=[f.name for f in args.extra_files if f.name],
        )
        invalidate_cache = True

    if args.cf_disabled:
        LOGGER.info("STATIC WEBSITE URL: %s", args.website_url)
    elif invalidate_cache:
        invalidate_distribution(
            session,
            identifier=args.distribution_id,
            domain=args.distribution_domain,
            path=args.distribution_path,
        )

    LOGGER.info("sync complete")

    if not build_context["deploy_is_current"]:
        update_ssm_hash(context, session)

    prune_archives(context, session)

    return True


def update_ssm_hash(context: CfnginContext, session: Session) -> bool:
    """Update the SSM hash with the new tracking data.

    Args:
        context: Context instance.
        session: boto3 session.

    """
    build_context = context.hook_data["staticsite"]

    if not build_context.get("hash_tracking_disabled"):
        hash_param = build_context["hash_tracking_parameter"]
        hash_value = build_context["hash"]

        LOGGER.info("updating SSM parameter %s with hash %s", hash_param, hash_value)

        set_ssm_value(
            session,
            hash_param,
            hash_value,
            "Hash of currently deployed static website source",
        )

    return True


def invalidate_distribution(
    session: Session,
    *,
    domain: str = "undefined",
    identifier: str,
    path: str = "/*",
    **_: Any,
) -> bool:
    """Invalidate the current distribution.

    Args:
        session: The current CFNgin session.
        domain: The distribution domain.
        identifier: The distribution id.
        path: The distribution path.

    """
    LOGGER.info("invalidating CloudFront distribution: %s (%s)", identifier, domain)
    cf_client = session.client("cloudfront")
    cf_client.create_invalidation(
        DistributionId=identifier,
        InvalidationBatch={
            "Paths": {"Quantity": 1, "Items": [path]},
            "CallerReference": str(time.time()),
        },
    )

    LOGGER.info("CloudFront invalidation complete")
    return True


def prune_archives(context: CfnginContext, session: Session) -> bool:
    """Prune the archives from the bucket.

    Args:
        context: The context instance.
        session: The CFNgin session.

    """
    LOGGER.info("cleaning up old site archives...")
    archives: list[dict[str, Any]] = []
    s3_client = session.client("s3")
    list_objects_v2_paginator = s3_client.get_paginator("list_objects_v2")
    response_iterator = list_objects_v2_paginator.paginate(
        Bucket=context.hook_data["staticsite"]["artifact_bucket_name"],
        Prefix=context.hook_data["staticsite"]["artifact_key_prefix"],
    )

    for page in response_iterator:
        archives.extend(page.get("Contents", []))  # type: ignore
    archives_to_prune = get_archives_to_prune(archives, context.hook_data["staticsite"])

    # Iterate in chunks of 1000 to match delete_objects limit
    for objects in [
        archives_to_prune[i : i + 1000] for i in range(0, len(archives_to_prune), 1000)
    ]:
        s3_client.delete_objects(
            Bucket=context.hook_data["staticsite"]["artifact_bucket_name"],
            Delete={"Objects": [{"Key": i} for i in objects]},
        )
    return True


def auto_detect_content_type(filename: str | None) -> str | None:
    """Auto detects the content type based on the filename.

    Args:
        filename : A filename to use to auto detect the content type.

    Returns:
        The content type of the file. None if the content type could not be detected.

    """
    if not filename:
        return None

    _, ext = os.path.splitext(filename)  # noqa: PTH122

    if ext == ".json":
        return "application/json"

    if ext in [".yml", ".yaml"]:
        return "text/yaml"

    return None


def get_content_type(extra_file: RunwayStaticSiteExtraFileDataModel) -> str | None:
    """Return the content type of the file.

    Args:
        extra_file: The extra file configuration.

    Returns:
        The content type of the extra file. If 'content_type' is provided then
        that is returned, otherwise it is auto detected based on the name.

    """
    return extra_file.content_type or auto_detect_content_type(extra_file.name)


def get_content(extra_file: RunwayStaticSiteExtraFileDataModel) -> str | None:
    """Get serialized content based on content_type.

    Args:
        extra_file: The extra file configuration.

    Returns:
        Serialized content based on the content_type.

    """
    if extra_file.content:
        if isinstance(extra_file.content, (dict, list)):
            if extra_file.content_type == "application/json":
                return json.dumps(extra_file.content)

            if extra_file.content_type == "text/yaml":
                return yaml.safe_dump(extra_file.content)

            raise ValueError('"content_type" must be json or yaml if "content" is not a string')

        if not isinstance(extra_file.content, str):
            raise TypeError(f"unsupported content: {type(extra_file.content)}")

    return cast("str | None", extra_file.content)


def calculate_hash_of_extra_files(
    extra_files: list[RunwayStaticSiteExtraFileDataModel],
) -> str:
    """Return a hash of all of the given extra files.

    All attributes of the extra file object are included when hashing:
    name, content_type, content, and file data.

    Args:
        extra_files: The list of extra file configurations.

    Returns:
        The hash of all the files.

    """
    file_hash = hashlib.md5()  # noqa: S324

    for extra_file in sorted(extra_files, key=lambda x: x.name):
        file_hash.update((extra_file.name + "\0").encode())

        if extra_file.content_type:
            file_hash.update((extra_file.content_type + "\0").encode())

        if extra_file.content:
            LOGGER.debug("hashing content: %s", extra_file.name)
            file_hash.update((cast(str, extra_file.content) + "\0").encode())

        if extra_file.file:
            with open(extra_file.file, "rb") as f:  # noqa: PTH123
                LOGGER.debug("hashing file: %s", extra_file.file)
                for chunk in iter(lambda: f.read(4096), ""):
                    if not chunk:
                        break
                    file_hash.update(chunk)
                file_hash.update(b"\0")

    return file_hash.hexdigest()


def get_ssm_value(session: Session, name: str) -> str | None:
    """Get the ssm parameter value.

    Args:
        session: The boto3 session.
        name: The parameter name.

    Returns:
        The parameter value.

    """
    ssm_client = session.client("ssm")

    try:
        return ssm_client.get_parameter(Name=name)["Parameter"].get("Value")
    except ssm_client.exceptions.ParameterNotFound:
        return None


def set_ssm_value(session: Session, name: str, value: Any, description: str = "") -> None:
    """Set the ssm parameter.

    Args:
        session: The boto3 session.
        name: The name of the parameter.
        value: The value of the parameter.
        description: A description of the parameter.

    """
    ssm_client = session.client("ssm")

    ssm_client.put_parameter(
        Name=name, Description=description, Value=value, Type="String", Overwrite=True
    )


def sync_extra_files(  # noqa: C901
    context: CfnginContext,
    bucket: str,
    extra_files: list[RunwayStaticSiteExtraFileDataModel],
    **kwargs: Any,
) -> list[str]:
    """Sync static website extra files to S3 bucket.

    Args:
        context: The context instance.
        bucket: The static site bucket name.
        extra_files: List of files and file content that should be uploaded.
        **kwargs: Arbitrary keyword arguments.

    """
    LOGGER.debug("extra_files to sync: %s", json.dumps(extra_files, cls=JsonEncoder))

    if not extra_files:
        return []

    session = context.get_session()
    s3_client = session.client("s3")
    uploaded: list[str] = []

    hash_param = cast(str, kwargs.get("hash_tracking_parameter", ""))
    hash_new = None

    # serialize content based on content type
    for extra_file in extra_files:
        extra_file.content_type = get_content_type(extra_file)
        extra_file.content = get_content(extra_file)

    # calculate a hash of the extra_files
    if hash_param:
        hash_param = f"{hash_param}extra"

        hash_old = get_ssm_value(session, hash_param)

        # calculate hash of content
        hash_new = calculate_hash_of_extra_files(extra_files)

        if hash_new == hash_old:
            LOGGER.info("skipped upload of extra files; latest version already deployed")
            return []

    for extra_file in extra_files:
        if extra_file.content:
            LOGGER.info("uploading extra file: %s", extra_file.name)

            s3_client.put_object(
                Bucket=bucket,
                Key=extra_file.name,
                Body=str(extra_file.content).encode(),
                ContentType=cast(str, extra_file.content_type),
            )

            uploaded.append(extra_file.name)

        if extra_file.file:
            LOGGER.info("uploading extra file: %s as %s ", extra_file.file, extra_file.name)

            extra_args = ""

            if extra_file.content_type:
                extra_args = {"ContentType": extra_file.content_type}

            if extra_args:
                s3_client.upload_file(
                    Bucket=bucket,
                    ExtraArgs=extra_args,
                    Filename=str(extra_file.file),
                    Key=extra_file.name,
                )
            if not extra_args:
                s3_client.upload_file(
                    Bucket=bucket,
                    Filename=str(extra_file.file),
                    Key=extra_file.name,
                )

            uploaded.append(extra_file.name)

    if hash_new:
        LOGGER.info("updating extra files SSM parameter %s with hash %s", hash_param, hash_new)
        set_ssm_value(session, hash_param, hash_new)

    return uploaded
