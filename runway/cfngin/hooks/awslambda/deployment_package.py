"""Deployment package."""

from __future__ import annotations

import base64
import hashlib
import logging
import mimetypes
import stat
import zipfile
from typing import TYPE_CHECKING, ClassVar, Final, Generic, TypeVar, cast, overload
from urllib.parse import urlencode

from ....compat import cached_property
from ....core.providers.aws.s3 import Bucket
from ....core.providers.aws.s3.exceptions import (
    BucketAccessDeniedError,
    BucketNotFoundError,
    S3ObjectDoesNotExistError,
)
from ....exceptions import RequiredTagNotFoundError
from ....mixins import DelCachedPropMixin
from ....utils import FileHash
from .base_classes import Project
from .exceptions import DeploymentPackageEmptyError
from .models.args import AwsLambdaHookArgs

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    import igittigitt
    from mypy_boto3_s3.type_defs import HeadObjectOutputTypeDef, PutObjectOutputTypeDef
    from typing_extensions import Literal

    from ...._logging import RunwayLogger

LOGGER = cast("RunwayLogger", logging.getLogger(__name__))


_ProjectTypeVar = TypeVar("_ProjectTypeVar", bound=Project[AwsLambdaHookArgs])


class DeploymentPackage(DelCachedPropMixin, Generic[_ProjectTypeVar]):
    """AWS Lambda Deployment Package.

    When interacting with subclass of this instance, it is recommended to
    only call the methods defined within this parent class. This ensures
    compatibility with the S3 object class that can be returned.

    """

    META_TAGS: ClassVar[dict[str, str]] = {
        "code_sha256": "runway.cfngin:awslambda.code_sha256",
        "compatible_architectures": "runway.cfngin:awslambda.compatible_architectures",
        "compatible_runtimes": "runway.cfngin:awslambda.compatible_runtimes",
        "license": "runway.cfngin:awslambda.license",
        "md5_checksum": "runway.cfngin:awslambda.md5_checksum",
        "runtime": "runway.cfngin:awslambda.runtime",
        "source_code.hash": "runway.cfngin:awslambda.source_code.hash",
    }
    """Mapping of metadata to the tag-key is is stored in on the S3 object."""

    SIZE_EOCD: Final[Literal[22]] = 22
    """Size of a zip file's End of Central Directory Record (empty zip)."""

    ZIPFILE_PERMISSION_MASK: ClassVar[int] = (stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO) << 16
    """Mask to retrieve unix file permissions from the external attributes
    property of a ``zipfile.ZipInfo``.
    """

    project: _ProjectTypeVar
    """Project that is being built into a deployment package."""

    usage_type: Literal["function", "layer"]
    """How the deployment package can be used by AWS Lambda."""

    _put_object_response: PutObjectOutputTypeDef | None = None

    def __init__(
        self,
        project: _ProjectTypeVar,
        usage_type: Literal["function", "layer"] = "function",
    ) -> None:
        """Instantiate class.

        The provided ``.init()`` class method should be used in place of
        direct instantiation.

        Args:
            project: Project that is being built into a deployment package.
            usage_type: How the deployment package can be used by AWS Lambda.

        """
        self.project = project
        self.usage_type = usage_type

    @cached_property
    def archive_file(self) -> Path:
        """Path to archive file.

        Because the archive file path contains runtime, it's use can cause a
        race condition or recursion error if used in some locations.
        If we removed runtime from the path we would not have a way to track
        changes to runtime which is more important than needing to be mindful
        of where this is used.

        """
        return self.project.build_directory / (
            f"{self.project.source_code.root_directory.name}."
            + ("layer." if self.usage_type == "layer" else "")
            + f"{self.runtime}.{self.project.source_code.md5_hash}.zip"
        )

    @cached_property
    def bucket(self) -> Bucket:
        """AWS S3 bucket where deployment package will be uploaded."""
        bucket = Bucket(self.project.ctx, self.project.args.bucket_name)
        if bucket.forbidden:
            raise BucketAccessDeniedError(bucket)
        if bucket.not_found:
            raise BucketNotFoundError(bucket)
        return bucket

    @cached_property
    def code_sha256(self) -> str:
        """SHA256 of the archive file.

        Returns:
            Value to pass to CloudFormation ``AWS::Lambda::Version.CodeSha256``.

        Raises:
            FileNotFoundError: Property accessed before archive file has been built.

        """
        file_hash = FileHash(hashlib.sha256())
        file_hash.add_file(self.archive_file)
        return base64.b64encode(file_hash.digest).decode()

    @cached_property
    def compatible_architectures(self) -> list[str] | None:
        """List of compatible instruction set architectures."""
        return self.project.compatible_architectures

    @cached_property
    def compatible_runtimes(self) -> list[str] | None:
        """List of compatible runtimes."""
        return self.project.compatible_runtimes

    @cached_property
    def exists(self) -> bool:
        """Whether the deployment package exists."""
        return bool(self.archive_file.exists())

    @cached_property
    def gitignore_filter(
        self,
    ) -> igittigitt.IgnoreParser | None:
        """Filter to use when zipping dependencies.

        This should be overridden by subclasses if a filter should be used.

        """
        return None

    @cached_property
    def license(self) -> str | None:
        """Software license for the project."""
        return self.project.license

    @cached_property
    def md5_checksum(self) -> str:
        """MD5 of the archive file.

        Returns:
            Value to pass as ContentMD5 when uploading to AWS S3.

        Raises:
            FileNotFoundError: Property accessed before archive file has been built.

        """
        file_hash = FileHash(hashlib.md5())  # noqa: S324
        file_hash.add_file(self.archive_file)
        return base64.b64encode(file_hash.digest).decode()

    @cached_property
    def object_key(self) -> str:
        """Key to use when upload object to AWS S3."""
        prefix = f"awslambda/{self.usage_type}s"
        if self.project.args.object_prefix:
            prefix = f"{prefix}/{self.project.args.object_prefix.lstrip('/').rstrip('/')}"
        return (  # this can't contain runtime - causes a cyclic dependency
            f"{prefix}/{self.project.source_code.root_directory.name}."
            f"{self.project.source_code.md5_hash}.zip"
        )

    @cached_property
    def object_version_id(self) -> str | None:
        """S3 object version ID.

        Returns:
            The ID of the current object version. This will only have a value
            if versioning is enabled on the bucket.

        """
        if not self._put_object_response or "VersionId" not in self._put_object_response:
            return None
        return self._put_object_response["VersionId"]

    @cached_property
    def runtime(self) -> str:
        """Runtime of the deployment package."""
        return self.project.runtime

    def build(self) -> Path:
        """Build the deployment package."""
        if self.exists and self.archive_file.stat().st_size > self.SIZE_EOCD:
            LOGGER.info("build skipped; %s already exists", self.archive_file.name)
            return self.archive_file

        # we need to use runtime BEFORE the build process starts to allow runtime
        # errors to be raised early.
        LOGGER.info("building %s (%s)...", self.archive_file.name, self.runtime)
        with zipfile.ZipFile(self.archive_file, "w", zipfile.ZIP_DEFLATED) as archive_file:
            self._build_zip_dependencies(archive_file)
            self._build_zip_source_code(archive_file)
            self._build_fix_file_permissions(archive_file)

        if self.archive_file.stat().st_size <= self.SIZE_EOCD:
            raise DeploymentPackageEmptyError(self.archive_file)

        # clear cached properties so they can recalculate
        self._del_cached_property("code_sha256", "exists", "md5_checksum")
        return self.archive_file

    def _build_fix_file_permissions(self, archive_file: zipfile.ZipFile) -> None:
        """Fix file permissions of the files contained within the archive file.

        Only need to ensure that the file is executable. Permissions will be
        change to 755 or 655 if needed. The change will occur within the
        archive file only - the original file will be unchanged.

        This should be run after all files have been added to the archive file.

        Args:
            archive_file: Archive file that is currently open and ready to be
                written to.

        """
        for file_info in archive_file.filelist:
            current_perms = (file_info.external_attr & self.ZIPFILE_PERMISSION_MASK) >> 16
            required_perm = 0o755 if current_perms & stat.S_IXUSR != 0 else 0o644
            if current_perms != required_perm:
                LOGGER.debug(
                    "fixing file permissions for %s: %o => %o",
                    file_info.filename,
                    current_perms,
                    required_perm,
                )
                file_info.external_attr = (
                    file_info.external_attr & ~self.ZIPFILE_PERMISSION_MASK
                ) | (required_perm << 16)

    def _build_zip_dependencies(
        self,
        archive_file: zipfile.ZipFile,
    ) -> None:
        """Handle installing & zipping dependencies.

        Args:
            archive_file: Archive file that is currently open and ready to be
                written to.

        """
        self.project.install_dependencies()
        for dep in self.iterate_dependency_directory():
            archive_file.write(
                dep,
                (
                    self.insert_layer_dir(dep, self.project.dependency_directory).relative_to(
                        self.project.dependency_directory
                    )
                    if self.usage_type == "layer"
                    else dep.relative_to(self.project.dependency_directory)
                ),
            )

    def _build_zip_source_code(self, archive_file: zipfile.ZipFile) -> None:
        """Handle zipping the project source code.

        Args:
            archive_file: Archive file that is currently open and ready to be
                written to.

        """
        for src_file in self.project.source_code:
            archive_file.write(
                src_file,
                (
                    self.insert_layer_dir(
                        src_file, self.project.source_code.root_directory
                    ).relative_to(self.project.source_code.root_directory)
                    if self.usage_type == "layer"
                    else src_file.relative_to(self.project.source_code.root_directory)
                ),
            )

    @overload
    def build_tag_set(self, *, url_encoded: Literal[True] = ...) -> str: ...

    @overload
    def build_tag_set(self, *, url_encoded: Literal[False] = ...) -> dict[str, str]: ...

    @overload
    def build_tag_set(self, *, url_encoded: bool = ...) -> dict[str, str] | str: ...

    def build_tag_set(self, *, url_encoded: bool = True) -> dict[str, str] | str:
        """Build tag set to be applied to the S3 object.

        Args:
            layer: Tag the deployment package as a Lambda Layer or not.
            url_encoded: Whether to return a dict or URL encoded query string.

        """
        optional_metadata = {
            self.META_TAGS["compatible_architectures"]: (
                "+".join(self.project.compatible_architectures)
                if self.project.compatible_architectures
                else None
            ),
            self.META_TAGS["compatible_runtimes"]: (
                "+".join(self.project.compatible_runtimes)
                if self.project.compatible_runtimes
                else None
            ),
            self.META_TAGS["license"]: self.project.license,
        }
        metadata = {
            self.META_TAGS["code_sha256"]: self.code_sha256,
            self.META_TAGS["md5_checksum"]: self.md5_checksum,
            self.META_TAGS["runtime"]: self.runtime,
            self.META_TAGS["source_code.hash"]: self.project.source_code.md5_hash,
        }
        tags = {
            **self.project.ctx.tags,
            **self.project.args.tags,
            **metadata,
            **{k: v for k, v in optional_metadata.items() if v},
        }
        if url_encoded:
            return urlencode(tags)
        return tags

    def delete(self) -> None:
        """Delete deployment package."""
        self.archive_file.unlink(missing_ok=True)
        LOGGER.verbose("deleted local deployment package %s", self.archive_file)
        # clear cached properties so they can recalculate
        self._del_cached_property("code_sha256", "exists", "md5_checksum", "object_version_id")

    @staticmethod
    def insert_layer_dir(file_path: Path, relative_to: Path) -> Path:  # noqa: ARG004
        """Insert directory into local file path for layer archive.

        If required, this should be overridden by a subclass for language
        specific requirements.

        Args:
            file_path: Path to local file.
            relative_to: Path to a directory that the file_path will be relative
                to in the deployment package.

        """
        return file_path

    def iterate_dependency_directory(self) -> Iterator[Path]:
        """Iterate over the contents of the dependency directory.

        If ``gitignore_filter`` is set, it will be used to exclude files.

        """
        for child in self.project.dependency_directory.rglob("*"):
            if child.is_dir():
                continue  # ignore directories
            if self.gitignore_filter and self.gitignore_filter.match(child):
                continue  # ignore files that match the filter
            yield child

    def upload(self, *, build: bool = True) -> None:
        """Upload deployment package.

        Args:
            build: If true, the deployment package will be built before before
                trying to upload it. If false, it must have already been built.

        """
        if build:
            self.build()

        # we don't really need encoding - it can be NoneType so throw it away
        content_type, _content_encoding = mimetypes.guess_type(self.archive_file)

        LOGGER.info(
            "uploading deployment package %s...",
            self.bucket.format_bucket_path_uri(key=self.object_key),
        )

        self._put_object_response = self.bucket.client.put_object(
            Body=self.archive_file.read_bytes(),
            Bucket=self.project.args.bucket_name,
            ContentMD5=self.md5_checksum,
            Key=self.object_key,
            Tagging=self.build_tag_set(),
            **(
                {"ContentType": content_type}  # pyright: ignore[reportArgumentType]
                if content_type
                else {}
            ),
        )
        # clear cached properties so they can recalculate
        self._del_cached_property("object_version_id")

    @classmethod
    def init(
        cls,
        project: _ProjectTypeVar,
        usage_type: Literal["function", "layer"] = "function",
    ) -> DeploymentPackage[_ProjectTypeVar]:
        """Initialize deployment package.

        This should be used in place of creating an instance of this class
        directly as it will automatically account for the S3 object already
        existing.

        Args:
            project: Project that is being built into a deployment package.
            usage_type: How the deployment package can be used by AWS Lambda.

        Returns:
            Instance of generic S3 object class if S3 object exists else
            an instance of this class.

        """
        s3_obj = DeploymentPackageS3Object(project, usage_type)
        if s3_obj.exists:
            if s3_obj.runtime == project.runtime:
                return s3_obj
            LOGGER.warning(
                "runtime of deployment package found in S3 (%s) does not match "
                "requirement (%s); deleting & recreating...",
                s3_obj.runtime,
                project.runtime,
            )
            s3_obj.delete()
        return cls(project, usage_type)


class DeploymentPackageS3Object(DeploymentPackage[_ProjectTypeVar]):
    """AWS Lambda Deployment Package.

    This should not need to be subclassed as the interactions required should
    be universal.

    Attributes:
        project: Project that is being built into a deployment package.

    """

    @cached_property
    def code_sha256(self) -> str:
        """SHA256 of the archive file.

        Returns:
            Value to pass to CloudFormation ``AWS::Lambda::Version.CodeSha256``.

        Raises:
            RequiredTagNotFound: A required tag was not found.

        """
        if self.META_TAGS["code_sha256"] not in self.object_tags:
            raise RequiredTagNotFoundError(
                self.bucket.format_bucket_path_uri(key=self.object_key),
                self.META_TAGS["code_sha256"],
            )
        return self.object_tags[self.META_TAGS["code_sha256"]]

    @cached_property
    def compatible_architectures(self) -> list[str] | None:
        """List of compatible instruction set architectures."""
        if self.META_TAGS["compatible_architectures"] in self.object_tags:
            return self.object_tags[self.META_TAGS["compatible_architectures"]].split("+")
        return None

    @cached_property
    def compatible_runtimes(self) -> list[str] | None:
        """List of compatible runtimes."""
        if self.META_TAGS["compatible_runtimes"] in self.object_tags:
            return self.object_tags[self.META_TAGS["compatible_runtimes"]].split("+")
        return None

    @cached_property
    def exists(self) -> bool:
        """Whether the S3 object exists."""
        return bool(self.head and not self.head.get("DeleteMarker", False))

    @cached_property
    def head(self) -> HeadObjectOutputTypeDef | None:
        """Response from HeadObject API call."""
        try:
            return self.bucket.client.head_object(Bucket=self.bucket.name, Key=self.object_key)
        except self.bucket.client.exceptions.ClientError as exc:
            status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0)
            if status_code == 404:
                LOGGER.verbose(
                    "%s not found",
                    self.bucket.format_bucket_path_uri(key=self.object_key),
                )
                return None
            if status_code == 403:
                # we can't handle this error but, we can enhance the error message
                LOGGER.error(
                    "access denied for object %s",
                    self.bucket.format_bucket_path_uri(key=self.object_key),
                )
            raise

    @cached_property
    def license(self) -> str | None:
        """Software license for the project."""
        if self.META_TAGS["license"] in self.object_tags:
            return self.object_tags[self.META_TAGS["license"]]
        return None

    @cached_property
    def md5_checksum(self) -> str:
        """MD5 of the archive file.

        Returns:
            Value to pass as ContentMD5 when uploading to AWS S3.

        Raises:
            RequiredTagNotFoundError: A required tag was not found.

        """
        if self.META_TAGS["md5_checksum"] not in self.object_tags:
            raise RequiredTagNotFoundError(
                self.bucket.format_bucket_path_uri(key=self.object_key),
                self.META_TAGS["md5_checksum"],
            )
        return self.object_tags[self.META_TAGS["md5_checksum"]]

    @cached_property
    def object_tags(self) -> dict[str, str]:
        """S3 object tags."""
        response = self.bucket.client.get_object_tagging(
            Bucket=self.bucket.name, Key=self.object_key
        )
        if "TagSet" not in response:
            # can't be hit when using botocore.stub.Stubber as TagSet is required
            return {}  # cov: ignore
        return {t["Key"]: t["Value"] for t in response["TagSet"]}

    @cached_property
    def object_version_id(self) -> str | None:
        """S3 object version ID.

        Returns:
            The ID of the current object version. This will only have a value
            if versioning is enabled on the bucket.

        """
        if not self.head or "VersionId" not in self.head:
            return None
        version_id = self.head["VersionId"]
        return version_id if version_id != "null" else None

    @cached_property
    def runtime(self) -> str:
        """Runtime of the deployment package.

        Raises:
            RequiredTagNotFoundError: A required tag was not found.

        """
        if self.META_TAGS["runtime"] not in self.object_tags:
            raise RequiredTagNotFoundError(
                self.bucket.format_bucket_path_uri(key=self.object_key),
                self.META_TAGS["runtime"],
            )
        return self.object_tags[self.META_TAGS["runtime"]]

    def build(self) -> Path:
        """Build the deployment package.

        The object should already exist. This method only exists as a "placeholder"
        to match the parent class. If the object does not already exist, and
        error is raised.

        Raises:
            S3ObjectDoesNotExistError: The S3 object does not exist.

        """
        if not self.exists:
            raise S3ObjectDoesNotExistError(self.bucket.name, self.object_key)
        LOGGER.info("build skipped; %s already exists", self.archive_file.name)
        return self.archive_file

    def delete(self) -> None:
        """Delete deployment package."""
        if self.exists:
            self.bucket.client.delete_object(Bucket=self.bucket.name, Key=self.object_key)
            LOGGER.verbose(
                "deleted deployment package S3 object %s",
                self.bucket.format_bucket_path_uri(key=self.object_key),
            )
            # clear cached properties so they can recalculate
            self._del_cached_property(
                "code_sha256",
                "exists",
                "md5_checksum",
                "object_tags",
                "object_version_id",
                "runtime",
            )

    def update_tags(self) -> None:
        """Update tags of the S3 object."""
        new_tags = self.build_tag_set(url_encoded=False)
        if new_tags == self.object_tags:
            LOGGER.debug(
                "%s tags don't need to be updated",
                self.bucket.format_bucket_path_uri(key=self.object_key),
            )
            return
        self.bucket.client.put_object_tagging(
            Bucket=self.bucket.name,
            Key=self.object_key,
            Tagging={"TagSet": [{"Key": k, "Value": v} for k, v in new_tags.items()]},
        )
        LOGGER.info("updated S3 object's tags")

    def upload(self, *, build: bool = True) -> None:  # noqa: ARG002
        """Upload deployment package.

        The object should already exist. This method only exists as a "placeholder"
        to match the parent class. If the object does not already exist, and
        error is raised.

        Args:
            build: If true, the deployment package will be built before before
                trying to upload it. If false, it must have already been built.

        Raises:
            S3ObjectDoesNotExistError: The S3 object does not exist.

        """
        if not self.exists:
            raise S3ObjectDoesNotExistError(self.bucket.name, self.object_key)
        LOGGER.info(
            "upload skipped; %s already exists",
            self.bucket.format_bucket_path_uri(key=self.object_key),
        )
        self.update_tags()
