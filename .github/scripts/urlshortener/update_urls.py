"""Update Runway release URLs."""
# pylint: disable=no-member
import logging
from typing import TYPE_CHECKING, Optional, Union

import boto3
import click
from semver import VersionInfo

if TYPE_CHECKING:  # only req boto3-stubs as a dev dependency
    from mypy_boto3.boto3_session import Session
    from mypy_boto3_dynamodb.service_resource import Table
else:
    Session = object
    Table = object

LOGGER = logging.getLogger("update_urls")
HDLR = logging.StreamHandler()
HDLR.setFormatter(logging.Formatter(logging.BASIC_FORMAT))

ID_TEMPLATE = "runway/{release}/{os}"
TARGET_TEMPLATE = (
    "https://{bucket_name}.s3-{region}.amazonaws.com/runway/{version}/{os}/runway"
)

OS_NAMES = ["linux", "osx", "windows"]


def sanitize_version(
    _ctx: Optional[click.Context],
    _param: Optional[Union[click.Option, click.Parameter]],
    value: str,
) -> str:
    """Sanitize a version number by stripping git tag ref and leading "v".

    To be used as the callback of a click option or parameter.

    Args:
        ctx: Click context object.
        param: The click option or parameter the callback is being used with.
        value: Value passed to the option or parameter from the CLI.

    Returns:
        str: The SemVer version number.

    """
    version = value.replace("refs/tags/", "")  # strip git ref
    if version.startswith("v"):  # strip leading "v"
        version = version[1:]
    if VersionInfo.isvalid(version):  # valid SemVer
        return version
    raise ValueError(f'version of "{version}" does not follow SemVer')


def put_item(table: Table, id_val: str, target: str) -> None:
    """Format and put a DDB entry."""
    LOGGER.info('Adding entry for "%s"...', id_val)
    table.put_item(Item={"id": id_val, "target": target}, ReturnValues="NONE")


def handler(
    table: Table,
    bucket_name: str,
    bucket_region: str,
    version: str,
    latest: bool = False,
) -> None:
    """Handle the command.

    Core logic executed by the command aside from boto3 session/resource
    initializeion and logging setup.

    Args:
        table: DynamoDB table resource.
        bucket_name: Name of S3 Bucket where Runway artifact is located
        bucket_region: AWS region where the S3 Bucket is located.
        version: SemVer version being release.
        latest: Update the "latest" URL.

    """
    for os_name in OS_NAMES:
        target = TARGET_TEMPLATE.format(
            bucket_name=bucket_name, os=os_name, region=bucket_region, version=version
        )
        if os_name == "windows":
            target += ".exe"
        if latest:
            put_item(
                table=table,
                id_val=ID_TEMPLATE.format(release="latest", os=os_name),
                target=target,
            )
        put_item(
            table=table,
            id_val=ID_TEMPLATE.format(release=version, os=os_name),
            target=target,
        )


@click.command(
    context_settings={
        "help_option_names": ["-h", "--help"],
        "max_content_width": 999,
        "show_default": True,
    }
)
@click.option(
    "-b",
    "--bucket-name",
    metavar="<bucket-name>",
    required=True,
    help="Name of S3 Bucket where Runway artifact is located.",
)
@click.option(
    "--bucket-region",
    metavar="<bucket-region>",
    required=True,
    help="AWS region where the S3 Bucket is located.",
)
@click.option("--latest", is_flag=True, help='Update the "latest" URL.')
@click.option(
    "--table",
    "table_name",
    metavar="<table>",
    required=True,
    help="Name of the DynamoDB table containing entries for the URL " "shortener.",
)
@click.option(
    "--version",
    metavar="<version>",
    required=True,
    callback=sanitize_version,
    help="Runway version being release.",
)
@click.option(
    "--table-region",
    metavar="<table-region>",
    default="us-east-1",
    help="AWS region where the DynamoDB table is located.",
)
def command(
    bucket_name: str,
    bucket_region: str,
    latest: bool,
    table_name: str,
    version: str,
    table_region: str = "us-east-1",
) -> None:
    """Update/add URLs to the URL shortener."""
    logging.basicConfig(level=logging.INFO, handlers=[HDLR])
    logging.getLogger("botocore").setLevel(logging.ERROR)

    session: Session = boto3.session.Session(region_name=table_region)
    table: Table = session.resource("dynamodb").Table(table_name)

    handler(table, bucket_name, bucket_region, version, latest)


if __name__ == "__main__":
    command()  # pylint: disable=E
