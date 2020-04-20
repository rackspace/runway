"""Update Runway release URLs."""
# pylint: disable=no-member
import logging
from typing import TypedDict

import boto3
import click
from mypy_boto3.boto3_session import Session
from mypy_boto3_dynamodb.service_resource import Table

LOGGER = logging.getLogger('update_urls')
HDLR = logging.StreamHandler()
HDLR.setFormatter(logging.Formatter(logging.BASIC_FORMAT))

ID_TEMPLATE = 'runway/{release}/{os}'
TARGET_TEMPLATE = ('https://{bucket_name}.s3-{region}.amazonaws.com/runway/'
                   '{version}/{os}/runway')

OS_NAMES = ['linux', 'osx', 'windows']


class UrlDdbEntry(TypedDict):
    """DynamoDB entry for the URL shortener.

    Attributes:
        id: The path after oni.ca in the shortened URL.
        target: The URL that is resolved from the shortened URL.

    """

    id: str
    target: str


def put_item(table: Table, id_val: str, target: str) -> None:
    """Format and put a DDB entry."""
    LOGGER.info('Adding entry for "%s"...', id_val)
    table.put_item(Item={'id': id_val, 'target': target},
                   ReturnValues='NONE')


@click.command(context_settings={'help_option_names': ['-h', '--help'],
                                 'max_content_width': 999,
                                 'show_default': True})
@click.option('-b', '--bucket-name', metavar='<bucket-name>', required=True,
              help='Name of S3 Bucket where Runway artifact is located.')
@click.option('--bucket-region', metavar='<bucket-region>', required=True,
              help='AWS region where the S3 Bucket is located.')
@click.option('--latest', is_flag=True, help='Update the "latest" URL.')
@click.option('--table', 'table_name', metavar='<table>', required=True,
              help='Name of the DynamoDB table containing entries for the URL '
              'shortener.')
@click.option('--version', metavar='<version>', required=True,
              help='Runway version being release.')
@click.option('--table-region', metavar='<table-region>', default='us-east-1',
              help='AWS region where the DynamoDB table is located.')
def command(bucket_name: str,
            bucket_region: str,
            latest: bool,
            table_name: str,
            version: str,
            table_region: str = 'us-east-1'
            ) -> None:
    """CLI interface for this script file."""
    logging.basicConfig(level=logging.INFO,
                        handlers=[HDLR])
    logging.getLogger('botocore').setLevel(logging.ERROR)

    session: Session = boto3.session.Session(region_name=table_region)
    table: Table = session.resource('dynamodb').Table(table_name)

    for os_name in OS_NAMES:
        target = TARGET_TEMPLATE.format(bucket_name=bucket_name,
                                        os=os_name,
                                        region=bucket_region,
                                        version=version)
        if os_name == 'windows':
            target += '.exe'
        if latest:
            put_item(table=table,
                     id_val=ID_TEMPLATE.format(release='latest', os=os_name),
                     target=target)
        put_item(table=table,
                 id_val=ID_TEMPLATE.format(release=version, os=os_name),
                 target=target)


if __name__ == '__main__':
    command()  # pylint: disable=E
