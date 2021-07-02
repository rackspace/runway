"""CFNgin hook for building static website."""
from __future__ import annotations

import logging
import os
import tempfile
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

import boto3
from boto3.s3.transfer import S3Transfer  # type: ignore
from typing_extensions import TypedDict

from ....s3_utils import does_s3_object_exist, download_and_extract_to_mkdtemp
from ....utils import change_dir, run_commands
from ...lookups.handlers.rxref import RxrefLookup
from .utils import get_hash_of_files

if TYPE_CHECKING:
    from ....cfngin.providers.aws.default import Provider
    from ....context import CfnginContext

LOGGER = logging.getLogger(__name__)


def zip_and_upload(
    app_dir: str, bucket: str, key: str, session: Optional[boto3.Session] = None
) -> None:
    """Zip built static site and upload to S3."""
    s3_client = session.client("s3") if session else boto3.client("s3")
    transfer = S3Transfer(s3_client)  # type: ignore

    filedes, temp_file = tempfile.mkstemp()
    os.close(filedes)
    LOGGER.info("archiving %s to s3://%s/%s", app_dir, bucket, key)
    with zipfile.ZipFile(temp_file, "w", zipfile.ZIP_DEFLATED) as filehandle:
        with change_dir(app_dir):
            for dirname, _subdirs, files in os.walk("./"):
                if dirname != "./":
                    filehandle.write(dirname)
                for filename in files:
                    filehandle.write(os.path.join(dirname, filename))
    transfer.upload_file(temp_file, bucket, key)
    os.remove(temp_file)


_RequiredOptionsArgTypeDef = TypedDict(
    "OptionsArgTypeDef", name=str, namespace=str, path=str
)


class _OptionalOptionsArgTypeDef(TypedDict, total=False):
    """Optional OptionsArgTypeDef fields."""

    build_output: str
    build_steps: List[Union[str, List[str], Dict[str, Union[str, List[str]]]]]
    pre_build_steps: List[Union[str, List[str], Dict[str, Union[str, List[str]]]]]


class OptionsArgTypeDef(_OptionalOptionsArgTypeDef, _RequiredOptionsArgTypeDef):
    """Options argument type definition."""


def build(
    context: CfnginContext,
    provider: Provider,
    *,
    artifact_bucket_rxref_lookup: str,
    options: Optional[OptionsArgTypeDef] = None,
    **_: Any,
) -> Dict[str, Any]:
    """Build static site."""
    session = context.get_session()
    options = options or {
        "name": "undefined",
        "namespace": context.namespace,
        "path": str(context.config_path),
    }
    context_dict: Dict[str, Any] = {
        "artifact_key_prefix": f"{options['namespace']}-{options['name']}-"
    }

    default_param_name = f"{context_dict['artifact_key_prefix']}hash"

    if "build_output" in options:
        build_output = os.path.join(options["path"], options["build_output"])
    else:
        build_output = options["path"]

    context_dict["artifact_bucket_name"] = RxrefLookup.handle(
        artifact_bucket_rxref_lookup, provider=provider, context=context
    )

    if "pre_build_steps" in options and options["pre_build_steps"]:
        run_commands(options["pre_build_steps"], options["path"])

    context_dict["hash"] = get_hash_of_files(
        root_path=Path(options["path"]),
        directories=options.get("source_hashing", {}).get("directories"),
    )
    LOGGER.debug("application hash: %s", context_dict["hash"])

    # Now determine if the current staticsite has already been deployed
    if options.get("source_hashing", {}).get("enabled", True):
        context_dict["hash_tracking_parameter"] = options.get("source_hashing", {}).get(
            "parameter", default_param_name
        )

        ssm_client = session.client("ssm")

        try:
            old_parameter_value = ssm_client.get_parameter(
                Name=context_dict["hash_tracking_parameter"]
            )["Parameter"]["Value"]
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
        if "build_steps" in options and options["build_steps"]:
            LOGGER.info("build steps (in progress)")
            run_commands(options["build_steps"], options["path"])
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
