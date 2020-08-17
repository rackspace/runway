"""CFNgin utilities."""
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
import warnings
import zipfile
from collections import OrderedDict

import botocore.client
import botocore.exceptions
import dateutil
import yaml
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode

from .awscli_yamlhelper import yaml_parse
from .session_cache import get_session

LOGGER = logging.getLogger(__name__)


def camel_to_snake(name):
    """Convert CamelCase to snake_case.

    Args:
        name (str): The name to convert from CamelCase to snake_case.

    Returns:
        str: Converted string.

    """
    sub_str_1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", sub_str_1).lower()


def convert_class_name(kls):
    """Get a string that represents a given class.

    Args:
        kls (class): The class being analyzed for its name.

    Returns:
        str: The name of the given kls.

    """
    return camel_to_snake(kls.__name__)


def parse_zone_id(full_zone_id):
    """Parse the returned hosted zone id and returns only the ID itself."""
    return full_zone_id.split("/")[2]


def get_hosted_zone_by_name(client, zone_name):
    """Get the zone id of an existing zone by name.

    Args:
        client (:class:`botocore.client.Route53`): The connection used to
            interact with Route53's API.
        zone_name (str): The name of the DNS hosted zone to create.

    Returns:
        str: The Id of the Hosted Zone.

    """
    paginator = client.get_paginator("list_hosted_zones")

    for page in paginator.paginate():
        for zone in page["HostedZones"]:
            if zone["Name"] == zone_name:
                return parse_zone_id(zone["Id"])
    return None


def get_or_create_hosted_zone(client, zone_name):
    """Get the Id of an existing zone, or create it.

    Args:
        client (:class:`botocore.client.Route53`): The connection used to
            interact with Route53's API.
        zone_name (str): The name of the DNS hosted zone to create.

    Returns:
        str: The Id of the Hosted Zone.

    """
    zone_id = get_hosted_zone_by_name(client, zone_name)
    if zone_id:
        return zone_id

    LOGGER.debug("zone %s does not exist; creating", zone_name)

    reference = uuid.uuid4().hex

    response = client.create_hosted_zone(Name=zone_name, CallerReference=reference)

    return parse_zone_id(response["HostedZone"]["Id"])


class SOARecordText(object):  # pylint: disable=too-few-public-methods
    """Represents the actual body of an SOARecord."""

    def __init__(self, record_text):
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

    def __str__(self):
        """Contert an instance of this class to a string."""
        return "%s %s %s %s %s %s %s" % (
            self.nameserver,
            self.contact,
            self.serial,
            self.refresh,
            self.retry,
            self.expire,
            self.min_ttl,
        )


class SOARecord(object):  # pylint: disable=too-few-public-methods
    """Represents an SOA record."""

    def __init__(self, record):
        """Instantiate class."""
        self.name = record["Name"]
        self.text = SOARecordText(record["ResourceRecords"][0]["Value"])
        self.ttl = record["TTL"]


def get_soa_record(client, zone_id, zone_name):
    """Get the SOA record for zone_name from zone_id.

    Args:
        client (:class:`boto3.client.Client`): The connection used to
            interact with Route53's API.
        zone_id (str): The AWS Route53 zone id of the hosted zone to query.
        zone_name (str): The name of the DNS hosted zone to create.

    Returns:
        :class:`runway.cfngin.util.SOARecord`: An object representing the
        parsed SOA record returned from AWS Route53.

    """
    response = client.list_resource_record_sets(
        HostedZoneId=zone_id,
        StartRecordName=zone_name,
        StartRecordType="SOA",
        MaxItems="1",
    )
    return SOARecord(response["ResourceRecordSets"][0])


def create_route53_zone(client, zone_name):
    """Create the given zone_name if it doesn't already exists.

    Also sets the SOA negative caching TTL to something short (300 seconds).

    Args:
        client (:class:`boto3.client.Client`): The connection used to
            interact with Route53's API.
        zone_name (str): The name of the DNS hosted zone to create.

    Returns:
        str: The zone id returned from AWS for the existing, or newly
        created zone.

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


def merge_map(a, b):
    """Recursively merge elements of argument b into argument a.

    Primarily used for merging two dictionaries together, where dict b takes
    precedence over dict a. If 2 lists are provided, they are concatenated.

    """
    if isinstance(a, list) and isinstance(b, list):
        return a + b

    if not isinstance(a, dict) or not isinstance(b, dict):
        return b

    for key in b:
        a[key] = merge_map(a[key], b[key]) if key in a else b[key]
    return a


def yaml_to_ordered_dict(stream, loader=yaml.SafeLoader):
    """yaml.load alternative with preserved dictionary order.

    Args:
        stream (str): YAML string to load.
        loader (:class:`yaml.loader`): PyYAML loader class. Defaults to safe
            load.

    Returns:
        OrderedDict: Parsed YAML.

    """

    class OrderedUniqueLoader(loader):
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
        def _error_mapping_on_dupe(node, node_name):
            """Check mapping node for dupe children keys."""
            if isinstance(node, MappingNode):
                mapping = {}
                for val in node.value:
                    a = val[0]
                    b = mapping.get(a.value, None)
                    if b:
                        msg = "{} mapping cannot have duplicate keys {} {}"
                        raise ConstructorError(
                            msg.format(node_name, b.start_mark, a.start_mark)
                        )
                    mapping[a.value] = a

        def _validate_mapping(self, node, deep=False):
            if not isinstance(node, MappingNode):
                raise ConstructorError(
                    None,
                    None,
                    "expected a mapping node, but found %s" % node.id,
                    node.start_mark,
                )
            mapping = OrderedDict()
            for key_node, value_node in node.value:
                key = self.construct_object(key_node, deep=deep)
                try:
                    hash(key)
                except TypeError as exc:
                    raise ConstructorError(
                        "while constructing a mapping",
                        node.start_mark,
                        "found unhashable key (%s)" % exc,
                        key_node.start_mark,
                    )
                # prevent duplicate sibling keys for certain "keywords".
                if key in mapping and key in self.NO_DUPE_SIBLINGS:
                    msg = "{} key cannot have duplicate siblings {} {}"
                    raise ConstructorError(
                        msg.format(key, node.start_mark, key_node.start_mark)
                    )
                if key in self.NO_DUPE_CHILDREN:
                    # prevent duplicate children keys for this mapping.
                    self._error_mapping_on_dupe(value_node, key_node.value)
                value = self.construct_object(value_node, deep=deep)
                mapping[key] = value
            return mapping

        def construct_mapping(self, node, deep=False):
            """Override parent method to use OrderedDict."""
            if isinstance(node, MappingNode):
                self.flatten_mapping(node)
            return self._validate_mapping(node, deep=deep)

        def construct_yaml_map(self, node):
            data = OrderedDict()
            yield data
            value = self.construct_mapping(node)
            data.update(value)

    OrderedUniqueLoader.add_constructor(
        u"tag:yaml.org,2002:map", OrderedUniqueLoader.construct_yaml_map,
    )
    return yaml.load(stream, OrderedUniqueLoader)


def uppercase_first_letter(string_):
    """Return string with first character upper case."""
    return string_[0].upper() + string_[1:]


def cf_safe_name(name):
    """Convert a name to a safe string for a CloudFormation resource.

    Given a string, returns a name that is safe for use as a CloudFormation
    Resource. (ie: Only alphanumeric characters)

    """
    alphanumeric = r"[a-zA-Z0-9]+"
    parts = re.findall(alphanumeric, name)
    return "".join([uppercase_first_letter(part) for part in parts])


def get_config_directory():
    """Return the directory the config file is located in.

    This enables us to use relative paths in config values.

    """
    # avoid circular import
    from .commands.stacker import Stacker  # pylint: disable=import-outside-toplevel

    deprecation_msg = (
        "get_config_directory has been deprecated and will be "
        "removed in the next major release"
    )
    warnings.warn(deprecation_msg, DeprecationWarning)
    LOGGER.warning(deprecation_msg)
    command = Stacker()
    namespace = command.parse_args()
    return os.path.dirname(namespace.config.name)


def read_value_from_path(value):
    """Enable translators to read values from files.

    The value can be referred to with the `file://` prefix.

    Example:
        ::

            conf_key: ${kms file://kms_value.txt}

    """
    if value.startswith("file://"):
        path = value.split("file://", 1)[1]
        if os.path.isabs(path):
            read_path = path
        else:
            config_directory = get_config_directory()
            read_path = os.path.join(config_directory, path)
        with open(read_path) as read_file:
            value = read_file.read()
    return value


def get_client_region(client):
    """Get the region from a :class:`boto3.client.Client` object.

    Args:
        client (:class:`boto3.client.Client`): The client to get the region
            from.

    Returns:
        str: AWS region string.

    """
    return client._client_config.region_name


def get_s3_endpoint(client):
    """Get the s3 endpoint for the given :class:`boto3.client.Client` object.

    Args:
        client (:class:`boto3.client.Client`): The client to get the endpoint
            from.

    Returns:
        str: The AWS endpoint for the client.

    """
    return client._endpoint.host


def s3_bucket_location_constraint(region):
    """Return the appropriate LocationConstraint info for a new S3 bucket.

    When creating a bucket in a region OTHER than us-east-1, you need to
    specify a LocationConstraint inside the CreateBucketConfiguration argument.
    This function helps you determine the right value given a given client.

    Args:
        region (str): The region where the bucket will be created in.

    Returns:
        str: The string to use with the given client for creating a bucket.

    """
    if region == "us-east-1":
        return ""
    return region


def ensure_s3_bucket(s3_client, bucket_name, bucket_region, persist_graph=False):
    """Ensure an s3 bucket exists, if it does not then create it.

    Args:
        s3_client (:class:`botocore.client.Client`): An s3 client used to
            verify and create the bucket.
        bucket_name (str): The bucket being checked/created.
        bucket_region (str, optional): The region to create the bucket in. If
            not provided, will be determined by s3_client's region.
        persist_graph (bool): Check bucket for recommended settings.
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
        if err.response["Error"]["Message"] == "Not Found":
            # can't use s3_client.exceptions.NoSuchBucket here.
            # it does not work if the bucket was recently deleted.
            LOGGER.debug("Creating bucket %s.", bucket_name)
            create_args = {"Bucket": bucket_name}
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
        else:
            LOGGER.exception('error creating bucket "%s"', bucket_name)
        raise


def parse_cloudformation_template(template):
    """Parse CFN template string.

    Leverages the vendored aws-cli yamlhelper to handle JSON or YAML templates.

    Args:
        template (str): The template body.

    """
    return yaml_parse(template)


class Extractor(object):
    """Base class for extractors."""

    def __init__(self, archive=None):
        """Instantiate class.

        Args:
            archive (str): Archive path.

        """
        self.archive = archive

    def set_archive(self, dir_name):
        """Update archive filename to match directory name & extension.

        Args:
            dir_name (str): Archive directory name

        """
        self.archive = dir_name + self.extension()

    @staticmethod
    def extension():
        """Serve as placeholder; override this in subclasses."""
        return ""


class TarExtractor(Extractor):
    """Extracts tar archives."""

    def extract(self, destination):
        """Extract the archive."""
        with tarfile.open(self.archive, "r:") as tar:
            tar.extractall(path=destination)

    @staticmethod
    def extension():
        """Return archive extension."""
        return ".tar"


class TarGzipExtractor(Extractor):
    """Extracts compressed tar archives."""

    def extract(self, destination):
        """Extract the archive."""
        with tarfile.open(self.archive, "r:gz") as tar:
            tar.extractall(path=destination)

    @staticmethod
    def extension():
        """Return archive extension."""
        return ".tar.gz"


class ZipExtractor(Extractor):
    """Extracts zip archives."""

    def extract(self, destination):
        """Extract the archive."""
        with zipfile.ZipFile(self.archive, "r") as zip_ref:
            zip_ref.extractall(destination)

    @staticmethod
    def extension():
        """Return archive extension."""
        return ".zip"


class SourceProcessor(object):
    """Makes remote python package sources available in current environment."""

    ISO8601_FORMAT = "%Y%m%dT%H%M%SZ"

    def __init__(self, sources, cfngin_cache_dir=None):
        """Process a config's defined package sources.

        Args:
            sources (Dict[str, Any]): Package sources from CFNgin config
                dictionary.
            cfngin_cache_dir (str): Path where remote sources will be
                cached.

        """
        if not cfngin_cache_dir:
            cfngin_cache_dir = os.path.expanduser("~/.runway_cache")
        package_cache_dir = os.path.join(cfngin_cache_dir, "packages")
        self.cfngin_cache_dir = cfngin_cache_dir
        self.package_cache_dir = package_cache_dir
        self.sources = sources
        self.configs_to_merge = []
        self.create_cache_directories()

    def create_cache_directories(self):
        """Ensure that SourceProcessor cache directories exist."""
        if not os.path.isdir(self.package_cache_dir):
            if not os.path.isdir(self.cfngin_cache_dir):
                os.mkdir(self.cfngin_cache_dir)
            os.mkdir(self.package_cache_dir)

    def get_package_sources(self):
        """Make remote python packages available for local use."""
        # Checkout local modules
        for config in self.sources.get("local", []):
            self.fetch_local_package(config=config)
        # Checkout S3 repositories specified in config
        for config in self.sources.get("s3", []):
            self.fetch_s3_package(config=config)
        # Checkout git repositories specified in config
        for config in self.sources.get("git", []):
            self.fetch_git_package(config=config)

    def fetch_local_package(self, config):
        """Make a local path available to current CFNgin config.

        Args:
            config (Dict[str, Any]): 'local' path config dictionary.

        """
        # Update sys.path & merge in remote configs (if necessary)
        self.update_paths_and_config(
            config=config, pkg_dir_name=config["source"], pkg_cache_dir=os.getcwd()
        )

    def fetch_s3_package(self, config):
        """Make a remote S3 archive available for local use.

        Args:
            config (Dict[str, Any]): git config dictionary.

        """
        extractor_map = {
            ".tar.gz": TarGzipExtractor,
            ".tar": TarExtractor,
            ".zip": ZipExtractor,
        }
        extractor = None
        for suffix, class_ in extractor_map.items():
            if config["key"].endswith(suffix):
                extractor = class_()
                LOGGER.debug(
                    'using extractor %s for S3 object "%s" in bucket %s',
                    class_.__name__,
                    config["key"],
                    config["bucket"],
                )
                dir_name = self.sanitize_uri_path(
                    "s3-%s-%s" % (config["bucket"], config["key"][: -len(suffix)])
                )
                break

        if extractor is None:
            raise ValueError(
                'Archive type could not be determined for S3 object "%s" '
                "in bucket %s." % (config["key"], config["bucket"])
            )

        session = get_session(region=None)
        extra_s3_args = {}
        if config.get("requester_pays", False):
            extra_s3_args["RequestPayer"] = "requester"

        # We can skip downloading the archive if it's already been cached
        if config.get("use_latest", True):
            try:
                # LastModified should always be returned in UTC, but it doesn't
                # hurt to explicitly convert it to UTC again just in case
                modified_date = (
                    session.client("s3")
                    .head_object(
                        Bucket=config["bucket"], Key=config["key"], **extra_s3_args
                    )["LastModified"]
                    .astimezone(dateutil.tz.tzutc())
                )
            except botocore.exceptions.ClientError as client_error:
                LOGGER.error(
                    "error checking modified date of s3://%s/%s : %s",
                    config["bucket"],
                    config["key"],
                    client_error,
                )
                sys.exit(1)
            dir_name += "-%s" % modified_date.strftime(self.ISO8601_FORMAT)
        cached_dir_path = os.path.join(self.package_cache_dir, dir_name)
        if not os.path.isdir(cached_dir_path):
            LOGGER.debug(
                "remote package s3://%s/%s does not appear to have "
                "been previously downloaded; starting download and "
                "extraction to %s",
                config["bucket"],
                config["key"],
                cached_dir_path,
            )
            tmp_dir = tempfile.mkdtemp(prefix="cfngin")
            tmp_package_path = os.path.join(tmp_dir, dir_name)
            try:
                extractor.set_archive(os.path.join(tmp_dir, dir_name))
                LOGGER.debug(
                    "starting remote package download from S3 to %s "
                    'with extra S3 options "%s"',
                    extractor.archive,
                    str(extra_s3_args),
                )
                session.resource("s3").Bucket(config["bucket"]).download_file(
                    config["key"], extractor.archive, ExtraArgs=extra_s3_args
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
                shutil.move(tmp_package_path, self.package_cache_dir)
            finally:
                shutil.rmtree(tmp_dir)
        else:
            LOGGER.debug(
                "remote package s3://%s/%s appears to have "
                "been previously downloaded to %s; download skipped",
                config["bucket"],
                config["key"],
                cached_dir_path,
            )

        # Update sys.path & merge in remote configs (if necessary)
        self.update_paths_and_config(config=config, pkg_dir_name=dir_name)

    def fetch_git_package(self, config):
        """Make a remote git repository available for local use.

        Args:
            config (Dict[str, Any]): git config dictionary.

        """
        # only loading git here when needed to avoid load errors on systems
        # without git installed
        from git import Repo  # pylint: disable=import-outside-toplevel

        ref = self.determine_git_ref(config)
        dir_name = self.sanitize_git_path(uri=config["uri"], ref=ref)
        cached_dir_path = os.path.join(self.package_cache_dir, dir_name)

        # We can skip cloning the repo if it's already been cached
        if not os.path.isdir(cached_dir_path):
            LOGGER.debug(
                "remote repo %s does not appear to have been "
                "previously downloaded; starting clone to %s",
                config["uri"],
                cached_dir_path,
            )
            tmp_dir = tempfile.mkdtemp(prefix="cfngin")
            try:
                tmp_repo_path = os.path.join(tmp_dir, dir_name)
                with Repo.clone_from(config["uri"], tmp_repo_path) as repo:
                    repo.head.reference = ref
                    repo.head.reset(index=True, working_tree=True)
                shutil.move(tmp_repo_path, self.package_cache_dir)
            finally:
                shutil.rmtree(tmp_dir)
        else:
            LOGGER.debug(
                "remote repo %s appears to have been previously "
                "cloned to %s; download skipped",
                config["uri"],
                cached_dir_path,
            )

        # Update sys.path & merge in remote configs (if necessary)
        self.update_paths_and_config(config=config, pkg_dir_name=dir_name)

    def update_paths_and_config(self, config, pkg_dir_name, pkg_cache_dir=None):
        """Handle remote source defined sys.paths & configs.

        Args:
            config (Dict[str, Any]): Git config dictionary.
            pkg_dir_name (str): directory Name of the CFNgin archive.
            pkg_cache_dir (Optional[str]): Fully qualified path to CFNgin
                cache cache directory.

        """
        if pkg_cache_dir is None:
            pkg_cache_dir = self.package_cache_dir
        cached_dir_path = os.path.join(pkg_cache_dir, pkg_dir_name)

        # Add the appropriate directory (or directories) to sys.path
        if config.get("paths"):
            for path in config["paths"]:
                path_to_append = os.path.join(cached_dir_path, path)
                LOGGER.debug("appending to python sys.path: %s", path_to_append)
                sys.path.append(path_to_append)
        else:
            sys.path.append(cached_dir_path)

        # If the configuration defines a set of remote config yaml files to
        # include, add them to the list for merging
        if config.get("configs"):
            for config_filename in config["configs"]:
                self.configs_to_merge.append(
                    os.path.join(cached_dir_path, config_filename)
                )

    @staticmethod
    def git_ls_remote(uri, ref):
        """Determine the latest commit id for a given ref.

        Args:
            uri (str): Git URI.
            ref (str): Git ref.

        Returns:
            str: A commit id

        """
        LOGGER.debug("getting commit ID from repo: %s", " ".join(uri))
        ls_remote_output = subprocess.check_output(["git", "ls-remote", uri, ref])
        # incorrectly detected - https://github.com/PyCQA/pylint/issues/3045
        if b"\t" in ls_remote_output:  # pylint: disable=unsupported-membership-test
            commit_id = ls_remote_output.split(b"\t")[0]
            LOGGER.debug("matching commit id found: %s", commit_id)
            return commit_id
        raise ValueError('Ref "%s" not found for repo %s.' % (ref, uri))

    @staticmethod
    def determine_git_ls_remote_ref(config):
        """Determine the ref to be used with the "git ls-remote" command.

        Args:
            config (:class:`runway.cfngin.config.GitPackageSource`): Git
                config dictionary; 'branch' key is optional.

        Returns:
            str: A branch reference or "HEAD".

        """
        if config.get("branch"):
            ref = "refs/heads/%s" % config["branch"]
        else:
            ref = "HEAD"

        return ref

    def determine_git_ref(self, config):
        """Determine the ref to be used for ``git checkout``.

        Args:
            config (Dict[str, Any]): Git config dictionary.

        Returns:
            str: A commit id or tag name.

        """
        # First ensure redundant config keys aren't specified (which could
        # cause confusion as to which take precedence)
        ref_config_keys = 0
        for i in ["commit", "tag", "branch"]:
            if config.get(i):
                ref_config_keys += 1
        if ref_config_keys > 1:
            raise ImportError(
                "Fetching remote git sources failed: "
                "conflicting revisions (e.g. 'commit', 'tag', "
                "'branch') specified for a package source"
            )

        # Now check for a specific point in time referenced and return it if
        # present
        if config.get("commit"):
            ref = config["commit"]
        elif config.get("tag"):
            ref = config["tag"]
        else:
            # Since a specific commit/tag point in time has not been specified,
            # check the remote repo for the commit id to use
            ref = self.git_ls_remote(
                config["uri"], self.determine_git_ls_remote_ref(config)
            )
        if sys.version_info[0] > 2 and isinstance(ref, bytes):
            return ref.decode()
        return ref

    @staticmethod
    def sanitize_uri_path(uri):
        """Take a URI and converts it to a directory safe path.

        Args:
            uri (str): URI (e.g. http://example.com/cats).

        Returns:
            str: Directory name for the supplied uri.

        """
        for i in ["@", "/", ":"]:
            uri = uri.replace(i, "_")
        return uri

    def sanitize_git_path(self, uri, ref=None):
        """Take a git URI and ref and converts it to a directory safe path.

        Args:
            uri (str): Git URI. (e.g. ``git@github.com:foo/bar.git``)
            ref (Optional[str]): Git ref to be appended to the path.

        Returns:
            str: Directory name for the supplied uri

        """
        if uri.endswith(".git"):
            dir_name = uri[:-4]  # drop .git
        else:
            dir_name = uri
        dir_name = self.sanitize_uri_path(dir_name)
        if ref is not None:
            dir_name += "-%s" % ref
        return dir_name


def stack_template_key_name(blueprint):
    """Given a blueprint, produce an appropriate key name.

    Args:
        blueprint (:class:`runway.cfngin.blueprints.base.Blueprint`): The
            blueprint object to create the key from.

    Returns:
        str: Key name resulting from blueprint.

    """
    name = blueprint.name
    return "stack_templates/%s/%s-%s.json" % (
        blueprint.context.get_fqn(name),
        name,
        blueprint.version,
    )
