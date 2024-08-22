"""CFNgin hook for building static website."""

from __future__ import annotations

import logging
import os
import tempfile
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

import boto3
from boto3.s3.transfer import S3Transfer
from typing_extensions import TypedDict

from ....module.staticsite.options import RunwayStaticSiteSourceHashingDataModel
from ....s3_utils import does_s3_object_exist, download_and_extract_to_mkdtemp
from ....utils import change_dir, run_commands
from ...lookups.handlers.rxref import RxrefLookup
from ..base import HookArgsBaseModel
from .utils import get_hash_of_files

if TYPE_CHECKING:
    from ....cfngin.providers.aws.default import Provider
    from ....context import CfnginContext

LOGGER = logging.getLogger(__name__)


class HookArgsOptions(HookArgsBaseModel):
    """Hook arguments ``options`` block."""

    build_output: str | None = None
    """Path were the build static site will be stored locally before upload."""

    build_steps: list[str | list[str] | dict[str, str | list[str]]] = []
    """Steps to execute to build the static site."""

    name: str = "undefined"
    """Static site name."""

    namespace: str
    """Namespace of the static site."""

    path: str
    """Working directory/path to the static site's source code."""

    pre_build_steps: list[str | list[str] | dict[str, str | list[str]]] = []
    """Steps to run before building the static site."""

    source_hashing: RunwayStaticSiteSourceHashingDataModel = (
        RunwayStaticSiteSourceHashingDataModel()
    )
    """Settings for tracking the hash of the source code between runs."""


class HookArgs(HookArgsBaseModel):
    """Hook arguments."""

    artifact_bucket_rxref_lookup: str
    """Query for ``RxrefLookup`` to get artifact bucket."""

    options: HookArgsOptions
    """Hook ``options`` block."""


def zip_and_upload(
    app_dir: str, bucket: str, key: str, session: boto3.Session | None = None
) -> None:
    """Zip built static site and upload to S3."""
    s3_client = session.client("s3") if session else boto3.client("s3")
    transfer = S3Transfer(s3_client)

    filedes, temp_file = tempfile.mkstemp()
    os.close(filedes)
    LOGGER.info("archiving %s to s3://%s/%s", app_dir, bucket, key)
    with zipfile.ZipFile(temp_file, "w", zipfile.ZIP_DEFLATED) as filehandle, change_dir(app_dir):
        for dirname, _subdirs, files in os.walk("./"):
            if dirname != "./":
                filehandle.write(dirname)
            for filename in files:
                filehandle.write(os.path.join(dirname, filename))  # noqa: PTH118
    transfer.upload_file(temp_file, bucket, key)
    os.remove(temp_file)  # noqa: PTH107


class OptionsArgTypeDef(TypedDict, total=False):
    """Options argument type definition."""

    build_output: str
    build_steps: list[str | list[str] | dict[str, str | list[str]]]
    name: str
    namespace: str
    path: str
    pre_build_steps: list[str | list[str] | dict[str, str | list[str]]]


def build(
    context: CfnginContext,
    provider: Provider,
    *,
    options: OptionsArgTypeDef | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Build static site.

    Arguments parsed by :class:`~runway.cfngin.hooks.staticsite.build_staticsite.HookArgs`.

    """
    options = options or {}
    options.setdefault("namespace", context.namespace)
    options.setdefault("path", str(context.config_path))
    args = HookArgs.model_validate({"options": options, **kwargs})
    session = context.get_session()

    context_dict: dict[str, Any] = {
        "artifact_key_prefix": f"{args.options.namespace}-{args.options.name}-"
    }

    if args.options.build_output:
        build_output = os.path.join(args.options.path, args.options.build_output)  # noqa: PTH118
    else:
        build_output = args.options.path

    context_dict["artifact_bucket_name"] = RxrefLookup.handle(
        args.artifact_bucket_rxref_lookup, provider=provider, context=context
    )

    if args.options.pre_build_steps:
        run_commands(args.options.pre_build_steps, args.options.path)

    context_dict["hash"] = get_hash_of_files(
        root_path=Path(args.options.path),
        directories=options.get("source_hashing", {"directories": None}).get("directories"),
    )
    LOGGER.debug("application hash: %s", context_dict["hash"])

    # Now determine if the current staticsite has already been deployed
    if args.options.source_hashing.enabled:
        context_dict["hash_tracking_parameter"] = (
            args.options.source_hashing.parameter or f"{context_dict['artifact_key_prefix']}hash"
        )

        ssm_client = session.client("ssm")

        try:
            old_parameter_value = ssm_client.get_parameter(
                Name=context_dict["hash_tracking_parameter"]
            )["Parameter"].get("Value")
        except ssm_client.exceptions.ParameterNotFound:
            old_parameter_value = None
    else:
        context_dict["hash_tracking_disabled"] = True
        old_parameter_value = None

    context_dict["current_archive_filename"] = (
        context_dict["artifact_key_prefix"] + context_dict["hash"] + ".zip"
    )
    if old_parameter_value:
        context_dict["old_archive_filename"] = (
            context_dict["artifact_key_prefix"] + old_parameter_value + ".zip"
        )

    if old_parameter_value == context_dict["hash"]:
        LOGGER.info("skipped build; hash already deployed")
        context_dict["deploy_is_current"] = True
        return context_dict

    if does_s3_object_exist(
        context_dict["artifact_bucket_name"],
        context_dict["current_archive_filename"],
        session,
    ):
        context_dict["app_directory"] = download_and_extract_to_mkdtemp(
            context_dict["artifact_bucket_name"],
            context_dict["current_archive_filename"],
            session,
        )
    else:
        if args.options.build_steps:
            LOGGER.info("build steps (in progress)")
            run_commands(args.options.build_steps, args.options.path)
            LOGGER.info("build steps (complete)")
        zip_and_upload(
            build_output,
            context_dict["artifact_bucket_name"],
            context_dict["current_archive_filename"],
            session,
        )
        context_dict["app_directory"] = build_output

    context_dict["deploy_is_current"] = False
    return context_dict
