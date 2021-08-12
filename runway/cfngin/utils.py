"""CFNgin utilities."""
from __future__ import annotations

import copy
import logging
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import uuid
import zipfile
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    Iterator,
    List,
    Optional,
    OrderedDict,
    Type,
    Union,
    cast,
)

import botocore.client
import botocore.exceptions
import dateutil
import yaml
from yaml.constructor import ConstructorError

from .awscli_yamlhelper import yaml_parse
from .session_cache import get_session

if TYPE_CHECKING:
    from mypy_boto3_route53.client import Route53Client
    from mypy_boto3_route53.type_defs import ResourceRecordSetTypeDef
    from mypy_boto3_s3.client import S3Client

    from ..config.models.cfngin import (
        CfnginPackageSourcesDefinitionModel,
        GitCfnginPackageSourceDefinitionModel,
        LocalCfnginPackageSourceDefinitionModel,
        S3CfnginPackageSourceDefinitionModel,
    )
    from .blueprints.base import Blueprint

LOGGER = logging.getLogger(__name__)


def camel_to_snake(name: str) -> str:
    """Convert CamelCase to snake_case.

    Args:
        name (str): The name to convert from CamelCase to snake_case.

    Returns:
        str: Converted string.

    """
    sub_str_1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", sub_str_1).lower()


def convert_class_name(kls: type) -> str:
    """Get a string that represents a given class.

    Args:
        kls: The class being analyzed for its name.

    Returns:
        The name of the given kls.

    """
    return camel_to_snake(kls.__name__)


def parse_zone_id(full_zone_id: str) -> str:
    """Parse the returned hosted zone id and returns only the ID itself."""
    return full_zone_id.split("/")[2]


def get_hosted_zone_by_name(client: Route53Client, zone_name: str) -> Optional[str]:
    """Get the zone id of an existing zone by name.

    Args:
        client: The connection used to interact with Route53's API.
        zone_name: The name of the DNS hosted zone to create.

    Returns:
        The Id of the Hosted Zone.

    """
    paginator = client.get_paginator("list_hosted_zones")

    for page in paginator.paginate():
        for zone in page["HostedZones"]:
            if zone["Name"] == zone_name:
                return parse_zone_id(zone["Id"])
    return None


def get_or_create_hosted_zone(client: Route53Client, zone_name: str) -> str:
    """Get the Id of an existing zone, or create it.

    Args:
        client: The connection used to interact with Route53's API.
        zone_name: The name of the DNS hosted zone to create.

    Returns:
        The Id of the Hosted Zone.

    """
    zone_id = get_hosted_zone_by_name(client, zone_name)
    if zone_id:
        return zone_id

    LOGGER.debug("zone %s does not exist; creating", zone_name)

    reference = uuid.uuid4().hex

    response = client.create_hosted_zone(Name=zone_name, CallerReference=reference)

    return parse_zone_id(response["HostedZone"]["Id"])


class SOARecordText:
    """Represents the actual body of an SOARecord."""

    def __init__(self, record_text: str) -> None:
        """Instantiate class."""
        (
            self.nameserver,
            self.contact,
            self.serial,
            self.refresh,
            self.retry,
            self.expire,
            self.min_ttl,
        ) = record_text.split()

    def __str__(self) -> str:
        """Convert an instance of this class to a string."""
        return " ".join(
            [
                self.nameserver,
                self.contact,
                self.serial,
                self.refresh,
                self.retry,
                self.expire,
                self.min_ttl,
            ]
        )


class SOARecord:
    """Represents an SOA record."""

    def __init__(self, record: ResourceRecordSetTypeDef) -> None:
        """Instantiate class."""
        self.name = record["Name"]
        self.text = SOARecordText(record.get("ResourceRecords", [{}])[0]["Value"])
        self.ttl = record.get("TTL", 0)


def get_soa_record(client: Route53Client, zone_id: str, zone_name: str) -> SOARecord:
    """Get the SOA record for zone_name from zone_id.

    Args:
        client: The connection used to interact with Route53's API.
        zone_id: The AWS Route53 zone id of the hosted zone to query.
        zone_name: The name of the DNS hosted zone to create.

    Returns:
        An object representing the parsed SOA record returned from AWS Route53.

    """
    response = client.list_resource_record_sets(
        HostedZoneId=zone_id,
        StartRecordName=zone_name,
        StartRecordType="SOA",
        MaxItems="1",
    )
    return SOARecord(response["ResourceRecordSets"][0])


def create_route53_zone(client: Route53Client, zone_name: str) -> str:
    """Create the given zone_name if it doesn't already exists.

    Also sets the SOA negative caching TTL to something short (300 seconds).

    Args:
        client: The connection used to interact with Route53's API.
        zone_name: The name of the DNS hosted zone to create.

    Returns:
        The zone id returned from AWS for the existing, or newly created zone.

    """
    if not zone_name.endswith("."):
        zone_name += "."
    zone_id = get_or_create_hosted_zone(client, zone_name)
    old_soa = get_soa_record(client, zone_id, zone_name)

    # If the negative cache value is already 300, don't update it.
    if old_soa.text.min_ttl == "300":
        return zone_id

    new_soa = copy.deepcopy(old_soa)
    LOGGER.debug("updating negative caching value on zone %s to 300", zone_name)
    new_soa.text.min_ttl = "300"
    client.change_resource_record_sets(
        HostedZoneId=zone_id,
        ChangeBatch={
            "Comment": "Update SOA min_ttl to 300.",
            "Changes": [
                {
                    "Action": "UPSERT",
                    "ResourceRecordSet": {
                        "Name": zone_name,
                        "Type": "SOA",
                        "TTL": old_soa.ttl,
                        "ResourceRecords": [{"Value": str(new_soa.text)}],
                    },
                },
            ],
        },
    )
    return zone_id


def yaml_to_ordered_dict(
    stream: str,
    loader: Union[Type[yaml.Loader], Type[yaml.SafeLoader]] = yaml.SafeLoader,
) -> OrderedDict[str, Any]:
    """yaml.load alternative with preserved dictionary order.

    Args:
        stream: YAML string to load.
        loader: PyYAML loader class. Defaults to safe load.

    """

    class OrderedUniqueLoader(loader):  # type: ignore
        """Subclasses the given pyYAML `loader` class.

        Validates all sibling keys to insure no duplicates.

        Returns:
            OrderedDict: instead of a Dict.

        """

        # keys which require no duplicate siblings.
        NO_DUPE_SIBLINGS = ["stacks", "class_path"]
        # keys which require no duplicate children keys.
        NO_DUPE_CHILDREN = ["stacks"]

        @staticmethod
        def _error_mapping_on_dupe(
            node: Union[yaml.MappingNode, yaml.ScalarNode, yaml.SequenceNode],
            node_name: str,
        ) -> None:
            """Check mapping node for dupe children keys."""
            if isinstance(node, yaml.MappingNode):
                mapping: Dict[str, Any] = {}
                for val in node.value:
                    a = val[0]
                    b = mapping.get(a.value, None)
                    if b:
                        raise ConstructorError(
                            f"{node_name} mapping cannot have duplicate keys "
                            f"{b.start_mark} {a.start_mark}"
                        )
                    mapping[a.value] = a

        def _validate_mapping(
            self,
            node: Union[yaml.MappingNode, yaml.ScalarNode, yaml.SequenceNode],
            deep: bool = False,
        ) -> OrderedDict[Any, Any]:
            if not isinstance(node, yaml.MappingNode):
                raise ConstructorError(
                    None,
                    None,
                    f"expected a mapping node, but found {node.id}",
                    node.start_mark,
                )
            mapping: OrderedDict[Any, Any] = OrderedDict()
            for key_node, value_node in node.value:
                key = cast(object, self.construct_object(key_node, deep=deep))
                try:
                    hash(key)
                except TypeError as exc:
                    raise ConstructorError(
                        "while constructing a mapping",
                        node.start_mark,
                        f"found unhashable key ({exc})",
                        key_node.start_mark,
                    ) from exc
                # prevent duplicate sibling keys for certain "keywords".
                if key in mapping and key in self.NO_DUPE_SIBLINGS:
                    raise ConstructorError(
                        f"{key} key cannot have duplicate siblings "
                        f"{node.start_mark} {key_node.start_mark}"
                    )
                if key in self.NO_DUPE_CHILDREN:
                    # prevent duplicate children keys for this mapping.
                    self._error_mapping_on_dupe(value_node, key_node.value)
                value = cast(object, self.construct_object(value_node, deep=deep))
                mapping[key] = value
            return mapping

        def construct_mapping(
            self,
            node: Union[yaml.MappingNode, yaml.ScalarNode, yaml.SequenceNode],
            deep: bool = False,
        ) -> OrderedDict[Any, Any]:
            """Override parent method to use OrderedDict."""
            if isinstance(node, yaml.MappingNode):
                self.flatten_mapping(node)
            return self._validate_mapping(node, deep=deep)

        def construct_yaml_map(
            self, node: Union[yaml.MappingNode, yaml.ScalarNode, yaml.SequenceNode]
        ) -> Iterator[OrderedDict[Any, Any]]:
            data: OrderedDict[Any, Any] = OrderedDict()
            yield data
            value: OrderedDict[Any, Any] = self.construct_mapping(node)
            data.update(value)

    OrderedUniqueLoader.add_constructor(
        "tag:yaml.org,2002:map", OrderedUniqueLoader.construct_yaml_map
    )
    return yaml.load(stream, OrderedUniqueLoader)


def uppercase_first_letter(string_: str) -> str:
    """Return string with first character upper case."""
    return string_[0].upper() + string_[1:]


def cf_safe_name(name: str) -> str:
    """Convert a name to a safe string for a CloudFormation resource.

    Given a string, returns a name that is safe for use as a CloudFormation
    Resource. (ie: Only alphanumeric characters)

    """
    alphanumeric = r"[a-zA-Z0-9]+"
    parts = re.findall(alphanumeric, name)
    return "".join(uppercase_first_letter(part) for part in parts)


def read_value_from_path(value: str, *, root_path: Optional[Path] = None) -> str:
    """Enable translators to read values from files.

    The value can be referred to with the `file://` prefix.

    Example:
        ::

            conf_key: ${kms file://kms_value.txt}

    """
    if value.startswith("file://"):
        path = value.split("file://", 1)[1]
        if os.path.isabs(path):
            read_path = Path(path)
        else:
            root_path = root_path or Path.cwd()
            if root_path.is_dir():
                read_path = root_path / path
            else:
                read_path = root_path.parent / path
        if read_path.is_file():
            return read_path.read_text()
        if read_path.is_dir():
            raise ValueError(
                f"path must lead to a file not directory: {read_path.absolute()}"
            )
        raise ValueError(f"path does not exist: {read_path.absolute()}")
    return value


def get_client_region(client: Any) -> str:
    """Get the region from a boto3 client.

    Args:
        client: The client to get the region from.

    Returns:
        AWS region string.

    """
    return client._client_config.region_name  # type: ignore


def get_s3_endpoint(client: Any) -> str:
    """Get the s3 endpoint for the given boto3 client.

    Args:
        client: The client to get the endpoint from.

    Returns:
        The AWS endpoint for the client.

    """
    return client._endpoint.host  # type: ignore


def s3_bucket_location_constraint(region: Optional[str]) -> Optional[str]:
    """Return the appropriate LocationConstraint info for a new S3 bucket.

    When creating a bucket in a region OTHER than us-east-1, you need to
    specify a LocationConstraint inside the CreateBucketConfiguration argument.
    This function helps you determine the right value given a given client.

    Args:
        region: The region where the bucket will be created in.

    Returns:
        The string to use with the given client for creating a bucket.

    """
    if region == "us-east-1":
        return ""
    return region


def ensure_s3_bucket(
    s3_client: S3Client,
    bucket_name: str,
    bucket_region: Optional[str] = None,
    *,
    create: bool = True,
    persist_graph: bool = False,
) -> None:
    """Ensure an s3 bucket exists, if it does not then create it.

    Args:
        s3_client: An s3 client used to verify and create the bucket.
        bucket_name: The bucket being checked/created.
        bucket_region: The region to create the bucket in.
            If not provided, will be determined by s3_client's region.
        create: Whether to create the bucket if it does not exist.
        persist_graph: Check bucket for recommended settings.
            If creating a new bucket, it will be created with recommended
            settings.

    """
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        if persist_graph:
            response = s3_client.get_bucket_versioning(Bucket=bucket_name)
            state = response.get("Status", "disabled").lower()
            if state != "enabled":
                LOGGER.warning(
                    'versioning is %s on bucket "%s"; it is recommended to '
                    "enable versioning when using persistent graphs",
                    state,
                    bucket_name,
                )
            if response.get("MFADelete", "Disabled") != "Disabled":
                LOGGER.warning(
                    'MFADelete must be disabled on bucket "%s" when using '
                    "persistent graphs to allow for propper management of "
                    "the graphs",
                    bucket_name,
                )
    except botocore.exceptions.ClientError as err:
        if err.response["Error"]["Message"] == "Not Found" and create:
            # can't use s3_client.exceptions.NoSuchBucket here.
            # it does not work if the bucket was recently deleted.
            LOGGER.debug("creating bucket %s", bucket_name)
            create_args: Dict[str, Any] = {"Bucket": bucket_name}
            location_constraint = s3_bucket_location_constraint(bucket_region)
            if location_constraint:
                create_args["CreateBucketConfiguration"] = {
                    "LocationConstraint": location_constraint
                }
            s3_client.create_bucket(**create_args)
            if persist_graph:
                s3_client.put_bucket_versioning(
                    Bucket=bucket_name, VersioningConfiguration={"Status": "Enabled"}
                )
            return
        if err.response["Error"]["Message"] == "Forbidden":
            LOGGER.exception(
                "Access denied for bucket %s. Did you remember "
                "to use a globally unique name?",
                bucket_name,
            )
        elif err.response["Error"]["Message"] != "Not Found":
            LOGGER.exception('error creating bucket "%s"', bucket_name)
        raise


def parse_cloudformation_template(template: str) -> Dict[str, Any]:
    """Parse CFN template string.

    Leverages the vendored aws-cli yamlhelper to handle JSON or YAML templates.

    Args:
        template: The template body.

    """
    return yaml_parse(template)


class Extractor:
    """Base class for extractors."""

    extension: ClassVar[str] = ""

    def __init__(self, archive: Optional[Path] = None) -> None:
        """Instantiate class.

        Args:
            archive (str): Archive path.

        """
        self.archive = archive

    def set_archive(self, dir_name: Path) -> None:
        """Update archive filename to match directory name & extension.

        Args:
            dir_name: Archive directory name

        """
        self.archive = dir_name.with_suffix(self.extension)


class TarExtractor(Extractor):
    """Extracts tar archives."""

    extension: ClassVar[str] = ".tar"

    def extract(self, destination: Path) -> None:
        """Extract the archive."""
        with tarfile.open(self.archive, "r:") as tar:
            tar.extractall(path=destination)


class TarGzipExtractor(Extractor):
    """Extracts compressed tar archives."""

    extension: ClassVar[str] = ".tar.gz"

    def extract(self, destination: Path) -> None:
        """Extract the archive."""
        with tarfile.open(self.archive, "r:gz") as tar:
            tar.extractall(path=destination)


class ZipExtractor(Extractor):
    """Extracts zip archives."""

    extension: ClassVar[str] = ".zip"

    def extract(self, destination: Path) -> None:
        """Extract the archive."""
        if self.archive:
            with zipfile.ZipFile(self.archive, "r") as zip_ref:
                zip_ref.extractall(destination)


class SourceProcessor:
    """Makes remote python package sources available in current environment."""

    ISO8601_FORMAT = "%Y%m%dT%H%M%SZ"

    def __init__(
        self,
        sources: CfnginPackageSourcesDefinitionModel,
        cache_dir: Optional[Path] = None,
    ) -> None:
        """Process a config's defined package sources.

        Args:
            sources: Package sources from CFNgin config
                dictionary.
            cache_dir: Path where remote sources will be
                cached.

        """
        if not cache_dir:
            cache_dir = Path.cwd() / ".runway" / "cache"
        self.cache_dir = cache_dir
        self.package_cache_dir = cache_dir / "packages"
        self.sources = sources
        self.configs_to_merge: List[Path] = []
        self.create_cache_directories()

    def create_cache_directories(self) -> None:
        """Ensure that SourceProcessor cache directories exist."""
        self.package_cache_dir.mkdir(parents=True, exist_ok=True)

    def get_package_sources(self) -> None:
        """Make remote python packages available for local use."""
        # Checkout local modules
        for config in self.sources.local:
            self.fetch_local_package(config=config)
        # Checkout S3 repositories specified in config
        for config in self.sources.s3:
            self.fetch_s3_package(config=config)
        # Checkout git repositories specified in config
        for config in self.sources.git:
            self.fetch_git_package(config=config)

    def fetch_local_package(
        self, config: LocalCfnginPackageSourceDefinitionModel
    ) -> None:
        """Make a local path available to current CFNgin config.

        Args:
            config: Package source config.

        """
        # Update sys.path & merge in remote configs (if necessary)
        self.update_paths_and_config(
            config=config, pkg_dir_name=config.source, pkg_cache_dir=Path.cwd()
        )

    def fetch_s3_package(self, config: S3CfnginPackageSourceDefinitionModel) -> None:
        """Make a remote S3 archive available for local use.

        Args:
            config: Package source config.

        """
        extractor_map = {
            ".tar.gz": TarGzipExtractor,
            ".tar": TarExtractor,
            ".zip": ZipExtractor,
        }
        extractor = None
        dir_name = ""
        for suffix, class_ in extractor_map.items():
            if config.key.endswith(suffix):
                extractor = class_()
                LOGGER.debug(
                    'using extractor %s for S3 object "%s" in bucket %s',
                    class_.__name__,
                    config.key,
                    config.bucket,
                )
                dir_name = self.sanitize_uri_path(
                    f"s3-{config.bucket}-{config.key[: -len(suffix)]}"
                )
                break

        if extractor is None:
            raise ValueError(
                f'Archive type could not be determined for S3 object "{config.key}" '
                f"in bucket {config.bucket}."
            )

        session = get_session(region=None)
        extra_s3_args: Dict[str, Any] = {}
        if config.requester_pays:
            extra_s3_args["RequestPayer"] = "requester"

        # We can skip downloading the archive if it's already been cached
        if config.use_latest:
            try:
                # LastModified should always be returned in UTC, but it doesn't
                # hurt to explicitly convert it to UTC again just in case
                modified_date = (
                    session.client("s3")
                    .head_object(Bucket=config.bucket, Key=config.key, **extra_s3_args)[
                        "LastModified"
                    ]  # type: ignore
                    .astimezone(dateutil.tz.tzutc())  # type: ignore
                )
            except botocore.exceptions.ClientError as client_error:
                LOGGER.error(
                    "error checking modified date of s3://%s/%s : %s",
                    config.bucket,
                    config.key,
                    client_error,
                )
                sys.exit(1)
            dir_name += f"-{modified_date.strftime(self.ISO8601_FORMAT)}"
        cached_dir_path = self.package_cache_dir / dir_name
        if not cached_dir_path.is_dir():
            LOGGER.debug(
                "remote package s3://%s/%s does not appear to have "
                "been previously downloaded; starting download and "
                "extraction to %s",
                config.bucket,
                config.key,
                cached_dir_path,
            )
            tmp_dir = tempfile.mkdtemp(prefix="cfngin")
            tmp_package_path = os.path.join(tmp_dir, dir_name)
            with tempfile.TemporaryDirectory(prefix="runway-cfngin") as tmp_dir:
                tmp_package_path = Path(tmp_dir) / dir_name
                extractor.set_archive(tmp_package_path)
                LOGGER.debug(
                    "starting remote package download from S3 to %s "
                    'with extra S3 options "%s"',
                    extractor.archive,
                    str(extra_s3_args),
                )
                session.resource("s3").Bucket(config.bucket).download_file(
                    Key=config.key,
                    Filename=str(extractor.archive),
                    ExtraArgs=extra_s3_args,
                )
                LOGGER.debug(
                    "download complete; extracting downloaded package to %s",
                    tmp_package_path,
                )
                extractor.extract(tmp_package_path)
                LOGGER.debug(
                    "moving extracted package directory %s to the "
                    "CFNgin cache at %s",
                    dir_name,
                    self.package_cache_dir,
                )
                shutil.move(str(tmp_package_path), self.package_cache_dir)
        else:
            LOGGER.debug(
                "remote package s3://%s/%s appears to have "
                "been previously downloaded to %s; download skipped",
                config.bucket,
                config.key,
                cached_dir_path,
            )

        # Update sys.path & merge in remote configs (if necessary)
        self.update_paths_and_config(config=config, pkg_dir_name=dir_name)

    def fetch_git_package(self, config: GitCfnginPackageSourceDefinitionModel) -> None:
        """Make a remote git repository available for local use.

        Args:
            config: Package source config.

        """
        # only loading git here when needed to avoid load errors on systems
        # without git installed
        from git import Repo  # pylint: disable=import-outside-toplevel

        ref = self.determine_git_ref(config)
        dir_name = self.sanitize_git_path(uri=config.uri, ref=ref)
        cached_dir_path = self.package_cache_dir / dir_name

        # We can skip cloning the repo if it's already been cached
        if not cached_dir_path.is_dir():
            LOGGER.debug(
                "remote repo %s does not appear to have been "
                "previously downloaded; starting clone to %s",
                config.uri,
                cached_dir_path,
            )
            tmp_dir = tempfile.mkdtemp(prefix="cfngin")
            try:
                tmp_repo_path = os.path.join(tmp_dir, dir_name)
                with Repo.clone_from(config.uri, tmp_repo_path) as repo:
                    repo.head.reference = ref
                    repo.head.reset(index=True, working_tree=True)
                shutil.move(tmp_repo_path, self.package_cache_dir)
            finally:
                shutil.rmtree(tmp_dir)
        else:
            LOGGER.debug(
                "remote repo %s appears to have been previously "
                "cloned to %s; download skipped",
                config.uri,
                cached_dir_path,
            )

        # Update sys.path & merge in remote configs (if necessary)
        self.update_paths_and_config(config=config, pkg_dir_name=dir_name)

    def update_paths_and_config(
        self,
        config: Union[
            GitCfnginPackageSourceDefinitionModel,
            LocalCfnginPackageSourceDefinitionModel,
            S3CfnginPackageSourceDefinitionModel,
        ],
        pkg_dir_name: str,
        pkg_cache_dir: Optional[Path] = None,
    ) -> None:
        """Handle remote source defined sys.paths & configs.

        Args:
            config: Package source config.
            pkg_dir_name: Directory name of the CFNgin archive.
            pkg_cache_dir: Fully qualified path to CFNgin cache cache directory.

        """
        if not pkg_cache_dir:
            pkg_cache_dir = self.package_cache_dir
        cached_dir_path = pkg_cache_dir / pkg_dir_name

        # Add the appropriate directory (or directories) to sys.path
        if config.paths:
            for path in config.paths:
                path_to_append = (cached_dir_path / path).resolve()
                LOGGER.debug("appending to python sys.path: %s", path_to_append)
                sys.path.append(str(path_to_append))
        else:
            sys.path.append(str(cached_dir_path.resolve()))

        # If the configuration defines a set of remote config yaml files to
        # include, add them to the list for merging
        if config.configs:
            for config_filename in config.configs:
                self.configs_to_merge.append(cached_dir_path / config_filename)

    @staticmethod
    def git_ls_remote(uri: str, ref: str) -> str:
        """Determine the latest commit id for a given ref.

        Args:
            uri: Git URI.
            ref: Git ref.

        """
        LOGGER.debug("getting commit ID from repo: %s", " ".join(uri))
        ls_remote_output = subprocess.check_output(["git", "ls-remote", uri, ref])
        # incorrectly detected - https://github.com/PyCQA/pylint/issues/3045
        if b"\t" in ls_remote_output:  # pylint: disable=unsupported-membership-test
            commit_id = ls_remote_output.split(b"\t", maxsplit=1)[0]
            LOGGER.debug("matching commit id found: %s", commit_id)
            return commit_id.decode()
        raise ValueError(f'Ref "{ref}" not found for repo {uri}.')

    @staticmethod
    def determine_git_ls_remote_ref(
        config: GitCfnginPackageSourceDefinitionModel,
    ) -> str:
        """Determine the ref to be used with the "git ls-remote" command.

        Args:
            config: Git package source config.

        Returns:
            A branch reference or "HEAD".

        """
        return f"refs/heads/{config.branch}" if config.branch else "HEAD"

    def determine_git_ref(self, config: GitCfnginPackageSourceDefinitionModel) -> str:
        """Determine the ref to be used for ``git checkout``.

        Args:
            config: Git package source config.

        Returns:
            A commit id or tag name.

        """
        if config.commit:
            return config.commit
        if config.tag:
            return config.tag
        return self.git_ls_remote(  # get a commit id to use
            config.uri, self.determine_git_ls_remote_ref(config)
        )

    @staticmethod
    def sanitize_uri_path(uri: str) -> str:
        """Take a URI and converts it to a directory safe path.

        Args:
            uri: URI to sanitize.

        Returns:
            Directory name for the supplied uri.

        """
        for i in ["@", "/", ":"]:
            uri = uri.replace(i, "_")
        return uri

    def sanitize_git_path(self, uri: str, ref: Optional[str] = None) -> str:
        """Take a git URI and ref and converts it to a directory safe path.

        Args:
            uri: Git URI. (e.g. ``git@github.com:foo/bar.git``)
            ref: Git ref to be appended to the path.

        Returns:
            Directory name for the supplied uri

        """
        if uri.endswith(".git"):
            dir_name = uri[:-4]  # drop .git
        else:
            dir_name = uri
        dir_name = self.sanitize_uri_path(dir_name)
        if ref is not None:
            dir_name += f"-{ref}"
        return dir_name


def stack_template_key_name(blueprint: Blueprint) -> str:
    """Given a blueprint, produce an appropriate key name.

    Args:
        blueprint: The blueprint object to create the key from.

    Returns:
        Key name resulting from blueprint.

    """
    name = blueprint.name
    return f"stack_templates/{blueprint.context.get_fqn(name)}/{name}-{blueprint.version}.json"
