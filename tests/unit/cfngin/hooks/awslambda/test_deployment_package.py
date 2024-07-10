"""Test runway.cfngin.hooks.awslambda.deployment_package."""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast
from urllib.parse import urlencode

import igittigitt
import pytest
from botocore.exceptions import ClientError
from mock import MagicMock, Mock, PropertyMock, call
from typing_extensions import Literal

from runway._logging import LogLevels
from runway.cfngin.hooks.awslambda.base_classes import Project
from runway.cfngin.hooks.awslambda.deployment_package import (
    DeploymentPackage,
    DeploymentPackageS3Object,
)
from runway.cfngin.hooks.awslambda.exceptions import (
    DeploymentPackageEmptyError,
    RuntimeMismatchError,
)
from runway.cfngin.hooks.awslambda.models.args import AwsLambdaHookArgs
from runway.core.providers.aws.s3 import Bucket
from runway.core.providers.aws.s3.exceptions import (
    BucketAccessDeniedError,
    BucketNotFoundError,
    S3ObjectDoesNotExistError,
)
from runway.exceptions import RequiredTagNotFoundError

from .factories import MockProject

if TYPE_CHECKING:
    from botocore.stub import Stubber
    from mypy_boto3_s3.type_defs import PutObjectOutputTypeDef
    from pytest import LogCaptureFixture
    from pytest_mock import MockerFixture

    from runway.context import CfnginContext

MODULE = "runway.cfngin.hooks.awslambda.deployment_package"

ProjectTypeAlias = Project[AwsLambdaHookArgs]


@pytest.fixture(scope="function")
def project(cfngin_context: CfnginContext, tmp_path: Path) -> ProjectTypeAlias:
    """Mock project object."""
    args = AwsLambdaHookArgs(
        bucket_name="test-bucket",
        runtime="foobar3.8",
        source_code=tmp_path,
    )
    return MockProject(args, cfngin_context)


class TestDeploymentPackage:
    """Test DeploymentPackage."""

    def test___init__(self, project: ProjectTypeAlias) -> None:
        """Test __init__."""
        obj = DeploymentPackage(project)
        # only one attribute is currently set by this base class
        assert obj.project == project

    def test__build_fix_file_permissions(self, project: ProjectTypeAlias) -> None:
        """Test _build_fix_file_permissions."""
        file0 = Mock(external_attr=0o777 << 16)
        file1 = Mock(external_attr=0o755 << 16)
        archive_file = Mock(filelist=[file0, file1])

        obj = DeploymentPackage(project)
        obj._build_fix_file_permissions(archive_file)
        assert (file0.external_attr & DeploymentPackage.ZIPFILE_PERMISSION_MASK) >> 16 == 0o755
        assert (file0.external_attr & DeploymentPackage.ZIPFILE_PERMISSION_MASK) >> 16 == 0o755

    @pytest.mark.parametrize("usage_type", ["function", "layer"])
    def test__build_zip_dependencies(
        self,
        mocker: MockerFixture,
        project: ProjectTypeAlias,
        usage_type: Literal["function", "layer"],
    ) -> None:
        """Test _build_zip_dependencies."""
        archive_file = Mock()
        layer_return = [
            project.dependency_directory / "layer" / "foo",
            project.dependency_directory / "layer" / "bar" / "foo",
        ]
        mock_insert_layer_dir = mocker.patch.object(
            DeploymentPackage,
            "insert_layer_dir",
            side_effect=layer_return,
        )
        mock_install_dependencies = mocker.patch.object(project, "install_dependencies")
        mock_iterate_dependency_directory = mocker.patch.object(
            DeploymentPackage,
            "iterate_dependency_directory",
            return_value=[
                project.dependency_directory / "foo",
                project.dependency_directory / "bar" / "foo",
            ],
        )

        obj = DeploymentPackage(project, usage_type)
        obj._build_zip_dependencies(archive_file)
        mock_install_dependencies.assert_called_once_with()
        mock_iterate_dependency_directory.assert_called_once_with()
        if usage_type == "layer":
            mock_insert_layer_dir.assert_has_calls(
                [  # type: ignore
                    call(dep, project.dependency_directory)
                    for dep in mock_iterate_dependency_directory.return_value
                ]
            )
            archive_file.write.assert_has_calls(
                [
                    call(dep, layered_dep.relative_to(project.dependency_directory))
                    for dep, layered_dep in zip(
                        mock_iterate_dependency_directory.return_value, layer_return
                    )
                ]
            )
        else:
            mock_insert_layer_dir.assert_not_called()
            archive_file.write.assert_has_calls(
                [
                    call(dep, dep.relative_to(project.dependency_directory))
                    for dep in mock_iterate_dependency_directory.return_value
                ]
            )

    @pytest.mark.parametrize("usage_type", ["function", "layer"])
    def test__build_zip_source_code(
        self,
        mocker: MockerFixture,
        project: ProjectTypeAlias,
        usage_type: Literal["function", "layer"],
    ) -> None:
        """Test _build_zip_source_code."""
        archive_file = Mock()
        files = [
            project.source_code.root_directory / "foo",
            project.source_code.root_directory / "bar" / "foo",
        ]
        mocker.patch.object(
            project,
            "source_code",
            MagicMock(
                __iter__=Mock(return_value=iter(files)),
                root_directory=project.source_code.root_directory,
            ),
        )
        layer_return = [
            project.source_code.root_directory / "layer" / "foo",
            project.source_code.root_directory / "layer" / "bar" / "foo",
        ]
        mock_insert_layer_dir = mocker.patch.object(
            DeploymentPackage,
            "insert_layer_dir",
            side_effect=layer_return,
        )

        obj = DeploymentPackage(project, usage_type)
        obj._build_zip_source_code(archive_file)
        if usage_type == "layer":
            mock_insert_layer_dir.assert_has_calls(
                [  # type: ignore
                    call(src_file, project.source_code.root_directory) for src_file in files
                ]
            )
            archive_file.write.assert_has_calls(
                [
                    call(
                        src_file,
                        layered_file.relative_to(project.source_code.root_directory),
                    )
                    for src_file, layered_file in zip(files, layer_return)
                ]
            )
        else:
            mock_insert_layer_dir.assert_not_called()
            archive_file.write.assert_has_calls(
                [
                    call(
                        src_file,
                        src_file.relative_to(project.source_code.root_directory),
                    )
                    for src_file in files
                ]
            )

    @pytest.mark.parametrize("usage_type", ["function", "layer"])
    def test_archive_file(
        self, project: ProjectTypeAlias, usage_type: Literal["function", "layer"]
    ) -> None:
        """Test archive_file."""
        obj = DeploymentPackage(project, usage_type)
        assert obj.archive_file.parent == project.build_directory
        if usage_type == "function":
            assert obj.archive_file.name == (
                f"{project.source_code.root_directory.name}.{project.runtime}."
                f"{project.source_code.md5_hash}.zip"
            )
        else:
            assert obj.archive_file.name == (
                f"{project.source_code.root_directory.name}.layer."
                f"{project.runtime}.{project.source_code.md5_hash}.zip"
            )

    def test_bucket(self, mocker: MockerFixture, project: ProjectTypeAlias) -> None:
        """Test bucket."""
        bucket_class = mocker.patch(
            f"{MODULE}.Bucket", return_value=Mock(forbidden=False, not_found=False)
        )
        obj = DeploymentPackage(project)
        assert obj.bucket == bucket_class.return_value
        bucket_class.assert_any_call(project.ctx, project.args.bucket_name)

    def test_bucket_forbidden(self, mocker: MockerFixture, project: ProjectTypeAlias) -> None:
        """Test bucket."""
        mocker.patch(f"{MODULE}.Bucket", return_value=Mock(forbidden=True, not_found=False))
        with pytest.raises(BucketAccessDeniedError):
            assert DeploymentPackage(project).bucket

    def test_build(
        self,
        caplog: LogCaptureFixture,
        mocker: MockerFixture,
        project: ProjectTypeAlias,
    ) -> None:
        """Test build."""
        caplog.set_level(LogLevels.INFO, logger=MODULE)
        mock_zipfile = MagicMock()
        mock_zipfile.__enter__ = Mock(return_value=mock_zipfile)
        mock_zipfile_class = mocker.patch(
            "zipfile.ZipFile",
            return_value=mock_zipfile,
        )

        def _write_zip(package: DeploymentPackage[Any], archive_file: Mock) -> None:
            package.archive_file.write_text("test" * 8)
            assert archive_file is mock_zipfile

        mock_build_zip_dependencies = mocker.patch.object(
            DeploymentPackage, "_build_zip_dependencies"
        )
        mocker.patch.object(DeploymentPackage, "_build_zip_source_code", _write_zip)
        mock_build_fix_file_permissions = mocker.patch.object(
            DeploymentPackage, "_build_fix_file_permissions"
        )
        mock_del_cached_property = mocker.patch.object(DeploymentPackage, "_del_cached_property")

        obj = DeploymentPackage(project)
        assert obj.build() == obj.archive_file
        mock_zipfile_class.assert_called_once_with(obj.archive_file, "w", zipfile.ZIP_DEFLATED)
        mock_zipfile.__enter__.assert_called_once_with()
        mock_build_zip_dependencies.assert_called_once_with(mock_zipfile)
        mock_build_fix_file_permissions.assert_called_once_with(mock_zipfile)
        mock_del_cached_property.assert_called_once_with("code_sha256", "exists", "md5_checksum")
        assert f"building {obj.archive_file.name} ({obj.runtime})..." in caplog.messages

    def test_build_file_empty_after_build(
        self, mocker: MockerFixture, project: ProjectTypeAlias
    ) -> None:
        """Test build archive_file empty after building."""
        archive_file = project.build_directory / "foobar.zip"
        mocker.patch.object(DeploymentPackage, "archive_file", archive_file)

        def _write_zip(package: DeploymentPackage[Any], archive_file: Mock) -> None:
            package.archive_file.touch()

        mock_build_zip_dependencies = mocker.patch.object(
            DeploymentPackage, "_build_zip_dependencies"
        )
        mocker.patch.object(DeploymentPackage, "_build_zip_source_code", _write_zip)
        mock_build_fix_file_permissions = mocker.patch.object(
            DeploymentPackage, "_build_fix_file_permissions"
        )

        with pytest.raises(DeploymentPackageEmptyError):
            DeploymentPackage(project).build()
        mock_build_zip_dependencies.assert_called_once()
        mock_build_fix_file_permissions.assert_called_once()

    def test_build_file_exists(
        self,
        caplog: LogCaptureFixture,
        mocker: MockerFixture,
        project: ProjectTypeAlias,
    ) -> None:
        """Test build."""
        caplog.set_level(LogLevels.INFO, logger=MODULE)
        mock_zipfile_class = mocker.patch(
            "zipfile.ZipFile",
            return_value=MagicMock(),
        )
        obj = DeploymentPackage(project)
        obj.archive_file.write_text("test" * 8)
        assert obj.build() == obj.archive_file
        mock_zipfile_class.assert_not_called()
        assert f"build skipped; {obj.archive_file.name} already exists" in caplog.messages

    def test_build_raise_runtime_mismatch_error(
        self, mocker: MockerFixture, project: ProjectTypeAlias
    ) -> None:
        """Test build raise RuntimeMismatchError."""
        mocker.patch.object(
            DeploymentPackage,
            "runtime",
            PropertyMock(side_effect=RuntimeMismatchError("", "")),
        )
        mock_build_zip_dependencies = mocker.patch.object(
            DeploymentPackage, "_build_zip_dependencies"
        )
        mock_build_zip_source_code = mocker.patch.object(
            DeploymentPackage, "_build_zip_source_code"
        )
        mock_build_fix_file_permissions = mocker.patch.object(
            DeploymentPackage, "_build_fix_file_permissions"
        )
        with pytest.raises(RuntimeMismatchError):
            DeploymentPackage(project).build()
        mock_build_zip_dependencies.assert_not_called()
        mock_build_zip_source_code.assert_not_called()
        mock_build_fix_file_permissions.assert_not_called()

    @pytest.mark.parametrize("url_encoded", [False, True, False, True])
    def test_build_tag_set(
        self,
        mocker: MockerFixture,
        project: ProjectTypeAlias,
        url_encoded: bool,
    ) -> None:
        """Test build_tag_set."""
        code_sha256 = mocker.patch.object(DeploymentPackage, "code_sha256", "code_sha256")
        mocker.patch.object(project, "compatible_runtimes", ["compatible_runtimes"])
        md5_checksum = mocker.patch.object(DeploymentPackage, "md5_checksum", "md5_checksum")
        source_md5_hash = mocker.patch.object(project.source_code, "md5_hash", "source_code.hash")
        expected = {
            **project.ctx.tags,
            DeploymentPackage.META_TAGS["code_sha256"]: code_sha256,
            DeploymentPackage.META_TAGS["md5_checksum"]: md5_checksum,
            DeploymentPackage.META_TAGS["runtime"]: project.runtime,
            DeploymentPackage.META_TAGS["source_code.hash"]: source_md5_hash,
            DeploymentPackage.META_TAGS["compatible_runtimes"]: "compatible_runtimes",
        }

        obj = DeploymentPackage(project)
        assert obj.build_tag_set(url_encoded=url_encoded) == (
            urlencode(expected) if url_encoded else expected
        )

    def test_bucket_not_found(self, mocker: MockerFixture, project: ProjectTypeAlias) -> None:
        """Test bucket."""
        mocker.patch(f"{MODULE}.Bucket", return_value=Mock(forbidden=False, not_found=True))
        with pytest.raises(BucketNotFoundError):
            assert DeploymentPackage(project).bucket

    def test_code_sha256(self, mocker: MockerFixture, project: ProjectTypeAlias) -> None:
        """Test code_sha256."""
        archive_file = mocker.patch.object(DeploymentPackage, "archive_file", "archive_file")
        file_hash = Mock(digest="digest")
        mock_b64encode = mocker.patch("base64.b64encode", return_value=b"success")
        mock_file_hash_class = mocker.patch(f"{MODULE}.FileHash", return_value=file_hash)
        mock_sha256 = mocker.patch("hashlib.sha256")
        assert DeploymentPackage(project).code_sha256 == mock_b64encode.return_value.decode()
        mock_file_hash_class.assert_called_once_with(mock_sha256.return_value)
        file_hash.add_file.assert_called_once_with(archive_file)
        mock_b64encode.assert_called_once_with(file_hash.digest)

    def test_compatible_architectures(
        self, mocker: MockerFixture, project: ProjectTypeAlias
    ) -> None:
        """Test compatible_architectures."""
        mocker.patch.object(project, "compatible_architectures", ["foobar"])
        assert DeploymentPackage(project).compatible_architectures == ["foobar"]

    def test_compatible_runtimes(self, mocker: MockerFixture, project: ProjectTypeAlias) -> None:
        """Test compatible_runtimes."""
        mocker.patch.object(project, "compatible_runtimes", ["foobar"])
        assert DeploymentPackage(project).compatible_runtimes == ["foobar"]

    @pytest.mark.parametrize("should_exist", [False, True])
    def test_delete(
        self, mocker: MockerFixture, project: ProjectTypeAlias, should_exist: bool
    ) -> None:
        """Test delete."""
        mock_del_cached_property = mocker.patch.object(DeploymentPackage, "_del_cached_property")
        obj = DeploymentPackage(project)
        if should_exist:
            obj.archive_file.touch()
        assert not obj.delete()
        assert not obj.archive_file.exists()
        mock_del_cached_property.assert_called_once_with(
            "code_sha256", "exists", "md5_checksum", "object_version_id"
        )

    @pytest.mark.parametrize("should_exist", [False, True])
    def test_exists(self, project: ProjectTypeAlias, should_exist: bool) -> None:
        """Test exists."""
        obj = DeploymentPackage(project)
        if should_exist:
            obj.archive_file.touch()
        assert obj.exists is should_exist

    def test_gitignore_filter(self, project: ProjectTypeAlias) -> None:
        """Test gitignore_filter."""
        assert not DeploymentPackage(project).gitignore_filter

    @pytest.mark.parametrize("exists_in_s3, usage_type", [(False, "function"), (True, "layer")])
    def test_init(
        self,
        exists_in_s3: bool,
        mocker: MockerFixture,
        project: ProjectTypeAlias,
        usage_type: Literal["function", "layer"],
    ) -> None:
        """Test init where runtime always matches."""
        s3_obj = Mock(exists=exists_in_s3, runtime=project.runtime)
        s3_obj_class = mocker.patch(f"{MODULE}.DeploymentPackageS3Object", return_value=s3_obj)

        if exists_in_s3:
            assert DeploymentPackage.init(project, usage_type) == s3_obj
        else:
            assert isinstance(DeploymentPackage.init(project, usage_type), DeploymentPackage)
        s3_obj_class.assert_called_once_with(project, usage_type)

    def test_init_runtime_change(
        self,
        caplog: LogCaptureFixture,
        mocker: MockerFixture,
        project: ProjectTypeAlias,
    ) -> None:
        """Test init where runtime has changed and object exists in S3."""
        caplog.set_level(LogLevels.WARNING, logger=MODULE)
        s3_obj = Mock(exists=True, runtime="change")
        s3_obj_class = mocker.patch(f"{MODULE}.DeploymentPackageS3Object", return_value=s3_obj)
        assert isinstance(DeploymentPackage.init(project), DeploymentPackage)
        s3_obj_class.assert_called_once_with(project, "function")
        s3_obj.delete.assert_called_once_with()
        assert (
            f"runtime of deployment package found in S3 ({s3_obj.runtime}) "
            f"does not match requirement ({project.runtime}); deleting & "
            "recreating..." in caplog.messages
        )

    def test_insert_layer_dir(self, tmp_path: Path) -> None:
        """Test insert_layer_dir does nothing."""
        test_path = tmp_path / "test"
        assert DeploymentPackage.insert_layer_dir(test_path, tmp_path) == test_path

    def test_iterate_dependency_directory(
        self, mocker: MockerFixture, project: ProjectTypeAlias
    ) -> None:
        """Test iterate_dependency_directory."""
        tmp_dir = project.dependency_directory / "bar"
        tmp_dir.mkdir()
        file0 = project.dependency_directory / "foo.txt"
        file0.touch()
        file1 = tmp_dir / "foo.txt"
        file1.touch()
        (project.dependency_directory / "foobar.json").touch()
        gitignore_filter = igittigitt.IgnoreParser()
        gitignore_filter.add_rule("**/*.json", project.dependency_directory)
        mocker.patch.object(DeploymentPackage, "gitignore_filter", gitignore_filter)

        obj = DeploymentPackage(project)
        assert sorted(obj.iterate_dependency_directory()) == sorted([file0, file1])

    def test_license(self, mocker: MockerFixture, project: ProjectTypeAlias) -> None:
        """Test license."""
        mocker.patch.object(project, "license", "foobar")
        assert DeploymentPackage(project).license == "foobar"

    def test_md5_checksum(self, mocker: MockerFixture, project: ProjectTypeAlias) -> None:
        """Test md5_checksum."""
        archive_file = mocker.patch.object(DeploymentPackage, "archive_file", "archive_file")
        file_hash = Mock(digest="digest")
        mock_b64encode = mocker.patch("base64.b64encode", return_value=b"success")
        mock_file_hash_class = mocker.patch(f"{MODULE}.FileHash", return_value=file_hash)
        mock_md5 = mocker.patch("hashlib.md5")
        assert DeploymentPackage(project).md5_checksum == mock_b64encode.return_value.decode()
        mock_file_hash_class.assert_called_once_with(mock_md5.return_value)
        file_hash.add_file.assert_called_once_with(archive_file)
        mock_b64encode.assert_called_once_with(file_hash.digest)

    @pytest.mark.parametrize(
        "object_prefix, usage_type",
        [
            (None, "function"),
            ("bar", "function"),
            ("/bar/", "layer"),
            ("/bar/foo/", "layer"),
        ],
    )
    def test_object_key(
        self,
        project: ProjectTypeAlias,
        object_prefix: Optional[str],
        usage_type: Literal["function", "layer"],
    ) -> None:
        """Test object_key."""
        project.args.object_prefix = object_prefix
        obj = DeploymentPackage(project, usage_type)
        if object_prefix:
            expected_prefix = f"awslambda/{usage_type}s/{object_prefix.lstrip('/').rstrip('/')}"
        else:
            expected_prefix = f"awslambda/{usage_type}s"
        assert obj.object_key == (
            f"{expected_prefix}/{project.source_code.root_directory.name}."
            f"{project.source_code.md5_hash}.zip"
        )

    @pytest.mark.parametrize("response, expected", [({}, None), ({"VersionId": "foo"}, "foo")])
    def test_object_version_id(
        self,
        expected: Optional[str],
        mocker: MockerFixture,
        project: ProjectTypeAlias,
        response: Dict[str, Any],
    ) -> None:
        """Test object_version_id."""
        mocker.patch.object(DeploymentPackage, "_put_object_response", response)
        obj = DeploymentPackage(project)
        assert obj.object_version_id == expected

    def test_runtime(self, project: ProjectTypeAlias) -> None:
        """Test runtime."""
        assert DeploymentPackage(project).runtime == project.runtime

    @pytest.mark.parametrize("build", [False, True])
    def test_upload(self, build: bool, mocker: MockerFixture, project: ProjectTypeAlias) -> None:
        """Test upload."""
        mocker.patch.object(
            DeploymentPackage,
            "bucket",
            Bucket(project.ctx, project.args.bucket_name),
        )
        key = mocker.patch.object(DeploymentPackage, "object_key", "key")
        mock_build = mocker.patch.object(DeploymentPackage, "build", return_value=None)
        mock_build_tag_set = mocker.patch.object(
            DeploymentPackage,
            "build_tag_set",
            return_value="foo=bar",
        )
        mock_del_cached_property = mocker.patch.object(DeploymentPackage, "_del_cached_property")
        mock_guess_type = mocker.patch(
            "mimetypes.guess_type", return_value=("application/zip", None)
        )
        md5_checksum = mocker.patch.object(DeploymentPackage, "md5_checksum", "checksum")

        obj = DeploymentPackage(project)
        obj.archive_file.write_text("foobar")
        response: PutObjectOutputTypeDef = {  # type: ignore
            "BucketKeyEnabled": False,
            "ETag": "string",
            "Expiration": "string",
            "RequestCharged": "requester",
            "SSECustomerAlgorithm": "string",
            "SSECustomerKeyMD5": "string",
            "SSEKMSEncryptionContext": "string",
            "SSEKMSKeyId": "string",
            "ServerSideEncryption": "AES256",
            "VersionId": "string",
            "ResponseMetadata": {
                "HTTPHeaders": {"foo": "bar"},
                "HTTPStatusCode": 200,
                "HostId": "",
                "RequestId": "",
                "RetryAttempts": 0,
            },
        }

        stubber = cast("Stubber", project.ctx.add_stubber("s3"))  # type: ignore
        stubber.add_response(
            "put_object",
            response,  # type: ignore
            {
                "Body": obj.archive_file.read_bytes(),
                "Bucket": project.args.bucket_name,
                "ContentMD5": md5_checksum,
                "ContentType": mock_guess_type.return_value[0],
                "Key": key,
                "Tagging": mock_build_tag_set.return_value,
            },
        )
        with stubber:
            assert not obj.upload(build=build)
            if build:
                mock_build.assert_called_once_with()
            else:
                mock_build.assert_not_called()
            mock_guess_type.assert_called_once_with(obj.archive_file)
            mock_build_tag_set.assert_called_once_with()
            mock_del_cached_property.assert_called_once_with("object_version_id")
        stubber.assert_no_pending_responses()


class TestDeploymentPackageS3Object:
    """Test DeploymentPackageS3Object."""

    def test_build_exists(
        self,
        caplog: LogCaptureFixture,
        mocker: MockerFixture,
        project: ProjectTypeAlias,
    ) -> None:
        """Test build object exists."""
        caplog.set_level(LogLevels.INFO, logger=MODULE)
        mocker.patch.object(
            DeploymentPackageS3Object,
            "archive_file",
            project.build_directory / "archive_file",
        )
        mocker.patch.object(DeploymentPackageS3Object, "exists", True)
        obj = DeploymentPackageS3Object(project)
        assert obj.build() == obj.archive_file
        assert f"build skipped; {obj.archive_file.name} already exists" in caplog.messages

    def test_build_not_exists(self, mocker: MockerFixture, project: ProjectTypeAlias) -> None:
        """Test build object doesn't exist raises S3ObjectDoesNotExistError."""
        mocker.patch.object(DeploymentPackageS3Object, "exists", False)
        bucket = Bucket(project.ctx, project.args.bucket_name)
        mocker.patch.object(DeploymentPackageS3Object, "bucket", bucket)
        obj = DeploymentPackageS3Object(project)
        with pytest.raises(S3ObjectDoesNotExistError) as excinfo:
            obj.build()
        assert excinfo.value.bucket == bucket.name
        assert excinfo.value.key == obj.object_key

    def test_code_sha256(self, mocker: MockerFixture, project: ProjectTypeAlias) -> None:
        """Test code_sha256."""
        expected = "foobar"
        mocker.patch.object(
            DeploymentPackageS3Object,
            "object_tags",
            {DeploymentPackageS3Object.META_TAGS["code_sha256"]: expected},
        )
        assert DeploymentPackageS3Object(project).code_sha256 == expected

    def test_code_sha256_raise_required_tag_not_found(
        self, project: ProjectTypeAlias, mocker: MockerFixture
    ) -> None:
        """Test code_sha256."""
        mocker.patch.object(DeploymentPackageS3Object, "object_tags", {})
        bucket = mocker.patch.object(
            DeploymentPackageS3Object,
            "bucket",
            Mock(format_bucket_path_uri=Mock(return_value="uri")),
        )
        object_key = mocker.patch.object(DeploymentPackageS3Object, "object_key", "key")

        with pytest.raises(RequiredTagNotFoundError) as excinfo:
            assert DeploymentPackageS3Object(project).code_sha256
        bucket.format_bucket_path_uri.assert_called_once_with(key=object_key)
        assert excinfo.value.resource == bucket.format_bucket_path_uri.return_value
        assert excinfo.value.tag_key == DeploymentPackageS3Object.META_TAGS["code_sha256"]

    @pytest.mark.parametrize("value", ["foobar", None, "foo,bar"])
    def test_compatible_architectures(
        self, mocker: MockerFixture, project: ProjectTypeAlias, value: Optional[str]
    ) -> None:
        """Test compatible_architectures."""
        mocker.patch.object(
            DeploymentPackageS3Object,
            "object_tags",
            (
                {DeploymentPackageS3Object.META_TAGS["compatible_architectures"]: value}
                if value
                else {}
            ),
        )
        assert DeploymentPackageS3Object(project).compatible_architectures == (
            value.split(", ") if value else None
        )

    @pytest.mark.parametrize("value", ["foobar", None, "foo,bar"])
    def test_compatible_runtimes(
        self, mocker: MockerFixture, project: ProjectTypeAlias, value: Optional[str]
    ) -> None:
        """Test compatible_runtimes."""
        mocker.patch.object(
            DeploymentPackageS3Object,
            "object_tags",
            ({DeploymentPackageS3Object.META_TAGS["compatible_runtimes"]: value} if value else {}),
        )
        assert DeploymentPackageS3Object(project).compatible_runtimes == (
            value.split(", ") if value else None
        )

    @pytest.mark.parametrize("should_exist", [False, True])
    def test_delete(
        self, mocker: MockerFixture, project: ProjectTypeAlias, should_exist: bool
    ) -> None:
        """Test delete."""
        mocker.patch.object(
            DeploymentPackageS3Object,
            "bucket",
            Bucket(project.ctx, project.args.bucket_name),
        )
        mocker.patch.object(DeploymentPackageS3Object, "exists", should_exist)
        mock_del_cached_property = mocker.patch.object(
            DeploymentPackageS3Object, "_del_cached_property"
        )
        object_key = mocker.patch.object(DeploymentPackageS3Object, "object_key", "key")

        obj = DeploymentPackageS3Object(project)
        stubber = cast("Stubber", project.ctx.add_stubber("s3"))  # type: ignore
        if should_exist:
            stubber.add_response(
                "delete_object",
                {},
                {"Bucket": project.args.bucket_name, "Key": object_key},
            )
        with stubber:
            obj.delete()
        stubber.assert_no_pending_responses()
        if should_exist:
            mock_del_cached_property.assert_called_once_with(
                "code_sha256",
                "exists",
                "md5_checksum",
                "object_tags",
                "object_version_id",
                "runtime",
            )
        else:
            mock_del_cached_property.assert_not_called()

    @pytest.mark.parametrize(
        "head, expected",
        [
            ({}, False),
            ({"ETag": "foo"}, True),
            ({"DeleteMarker": True, "ETag": "bar"}, False),
        ],
    )
    def test_exists(
        self,
        expected: bool,
        head: Dict[str, Any],
        project: ProjectTypeAlias,
        mocker: MockerFixture,
    ) -> None:
        """Test exists."""
        mocker.patch.object(DeploymentPackageS3Object, "head", head)
        assert DeploymentPackageS3Object(project).exists is expected

    def test_head(self, mocker: MockerFixture, project: ProjectTypeAlias) -> None:
        """Test head."""
        mocker.patch.object(
            DeploymentPackageS3Object,
            "bucket",
            Bucket(project.ctx, project.args.bucket_name),
        )
        object_key = mocker.patch.object(DeploymentPackageS3Object, "object_key", "key")
        response = {"ETag": "foobar"}

        stubber = cast("Stubber", project.ctx.add_stubber("s3"))  # type: ignore
        stubber.add_response(
            "head_object",
            response,
            {"Bucket": project.args.bucket_name, "Key": object_key},
        )
        with stubber:
            assert DeploymentPackageS3Object(project).head == response
        stubber.assert_no_pending_responses()

    def test_head_403(
        self,
        caplog: LogCaptureFixture,
        mocker: MockerFixture,
        project: ProjectTypeAlias,
    ) -> None:
        """Test head 403."""
        caplog.set_level(LogLevels.ERROR, logger=MODULE)
        bucket = Bucket(project.ctx, project.args.bucket_name)
        mocker.patch.object(
            DeploymentPackageS3Object,
            "bucket",
            Bucket(project.ctx, project.args.bucket_name),
        )
        object_key = mocker.patch.object(DeploymentPackageS3Object, "object_key", "key")

        stubber = cast("Stubber", project.ctx.add_stubber("s3"))  # type: ignore
        stubber.add_client_error("head_object", http_status_code=403, service_message="Forbidden")
        with stubber, pytest.raises(ClientError):
            assert DeploymentPackageS3Object(project).head
        stubber.assert_no_pending_responses()
        assert (
            f"access denied for object {bucket.format_bucket_path_uri(key=object_key)}"
            in caplog.messages
        )

    def test_head_404(
        self,
        caplog: LogCaptureFixture,
        mocker: MockerFixture,
        project: ProjectTypeAlias,
    ) -> None:
        """Test head 404."""
        caplog.set_level(LogLevels.VERBOSE, logger=MODULE)
        bucket = Bucket(project.ctx, project.args.bucket_name)
        mocker.patch.object(
            DeploymentPackageS3Object,
            "bucket",
            Bucket(project.ctx, project.args.bucket_name),
        )
        object_key = mocker.patch.object(DeploymentPackageS3Object, "object_key", "key")

        stubber = cast("Stubber", project.ctx.add_stubber("s3"))  # type: ignore
        stubber.add_client_error("head_object", http_status_code=404, service_message="Not Found")
        with stubber:
            assert not DeploymentPackageS3Object(project).head
        stubber.assert_no_pending_responses()
        assert f"{bucket.format_bucket_path_uri(key=object_key)} not found" in caplog.messages

    @pytest.mark.parametrize("value", ["foobar", None])
    def test_license(
        self, mocker: MockerFixture, project: ProjectTypeAlias, value: Optional[str]
    ) -> None:
        """Test license."""
        mocker.patch.object(
            DeploymentPackageS3Object,
            "object_tags",
            {DeploymentPackageS3Object.META_TAGS["license"]: value} if value else {},
        )
        assert DeploymentPackageS3Object(project).license == (value)

    def test_md5_checksum(self, project: ProjectTypeAlias, mocker: MockerFixture) -> None:
        """Test md5_checksum."""
        expected = "foobar"
        mocker.patch.object(
            DeploymentPackageS3Object,
            "object_tags",
            {DeploymentPackageS3Object.META_TAGS["md5_checksum"]: expected},
        )
        assert DeploymentPackageS3Object(project).md5_checksum == expected

    def test_md5_checksum_raise_required_tag_not_found(
        self,
        mocker: MockerFixture,
        project: ProjectTypeAlias,
    ) -> None:
        """Test md5_checksum."""
        mocker.patch.object(DeploymentPackageS3Object, "object_tags", {})
        bucket = mocker.patch.object(
            DeploymentPackageS3Object,
            "bucket",
            Mock(format_bucket_path_uri=Mock(return_value="uri")),
        )
        object_key = mocker.patch.object(DeploymentPackageS3Object, "object_key", "key")

        with pytest.raises(RequiredTagNotFoundError) as excinfo:
            assert DeploymentPackageS3Object(project).md5_checksum
        bucket.format_bucket_path_uri.assert_called_once_with(key=object_key)
        assert excinfo.value.resource == bucket.format_bucket_path_uri.return_value
        assert excinfo.value.tag_key == DeploymentPackageS3Object.META_TAGS["md5_checksum"]

    @pytest.mark.parametrize(
        "response, expected",
        [
            ({"TagSet": [{"Key": "foo", "Value": "bar"}]}, {"foo": "bar"}),
            ({"TagSet": []}, {}),  # TagSet must be included for stubber
        ],
    )
    def test_object_tags(
        self,
        expected: Dict[str, str],
        mocker: MockerFixture,
        project: ProjectTypeAlias,
        response: Dict[str, List[Dict[str, str]]],
    ) -> None:
        """Test object_tags."""
        mocker.patch.object(
            DeploymentPackageS3Object,
            "bucket",
            Bucket(project.ctx, project.args.bucket_name),
        )
        object_key = mocker.patch.object(DeploymentPackageS3Object, "object_key", "key")

        stubber = cast("Stubber", project.ctx.add_stubber("s3"))  # type: ignore
        stubber.add_response(
            "get_object_tagging",
            response,
            {"Bucket": project.args.bucket_name, "Key": object_key},
        )
        with stubber:
            assert DeploymentPackageS3Object(project).object_tags == expected
        stubber.assert_no_pending_responses()

    @pytest.mark.parametrize(
        "head, expected",
        [({}, None), ({"ETag": "foo"}, None), ({"VersionId": "foo"}, "foo")],
    )
    def test_object_version_id(
        self,
        expected: Optional[str],
        head: Dict[str, str],
        mocker: MockerFixture,
        project: ProjectTypeAlias,
    ) -> None:
        """Test object_version_id."""
        mocker.patch.object(DeploymentPackageS3Object, "head", head)
        assert DeploymentPackageS3Object(project).object_version_id == expected

    def test_runtime(self, project: ProjectTypeAlias, mocker: MockerFixture) -> None:
        """Test runtime."""
        expected = "foobar"
        mocker.patch.object(
            DeploymentPackageS3Object,
            "object_tags",
            {DeploymentPackageS3Object.META_TAGS["runtime"]: expected},
        )
        assert DeploymentPackageS3Object(project).runtime == expected

    def test_runtime_raise_required_tag_not_found(
        self,
        mocker: MockerFixture,
        project: ProjectTypeAlias,
    ) -> None:
        """Test runtime."""
        mocker.patch.object(DeploymentPackageS3Object, "object_tags", {})
        bucket = mocker.patch.object(
            DeploymentPackageS3Object,
            "bucket",
            Mock(format_bucket_path_uri=Mock(return_value="uri")),
        )
        object_key = mocker.patch.object(DeploymentPackageS3Object, "object_key", "key")

        with pytest.raises(RequiredTagNotFoundError) as excinfo:
            assert DeploymentPackageS3Object(project).runtime
        bucket.format_bucket_path_uri.assert_called_once_with(key=object_key)
        assert excinfo.value.resource == bucket.format_bucket_path_uri.return_value
        assert excinfo.value.tag_key == DeploymentPackageS3Object.META_TAGS["runtime"]

    def test_update_tags(self, mocker: MockerFixture, project: ProjectTypeAlias) -> None:
        """Test mock_update_tags."""
        bucket = Bucket(project.ctx, project.args.bucket_name)
        mocker.patch.object(DeploymentPackageS3Object, "bucket", bucket)
        mocker.patch.object(DeploymentPackageS3Object, "object_tags", {"bar": "foo"})
        mock_build_tag_set = mocker.patch.object(
            DeploymentPackageS3Object, "build_tag_set", return_value={"foo": "bar"}
        )
        object_key = mocker.patch.object(DeploymentPackageS3Object, "object_key", "key")

        stubber = cast("Stubber", project.ctx.add_stubber("s3"))  # type: ignore
        stubber.add_response(
            "put_object_tagging",
            {"VersionId": ""},
            {
                "Bucket": project.args.bucket_name,
                "Key": object_key,
                "Tagging": {"TagSet": [{"Key": "foo", "Value": "bar"}]},
            },
        )
        with stubber:
            assert not DeploymentPackageS3Object(project).update_tags()
        mock_build_tag_set.assert_called_once_with(url_encoded=False)
        stubber.assert_no_pending_responses()

    def test_update_tags_no_change(
        self,
        caplog: LogCaptureFixture,
        mocker: MockerFixture,
        project: ProjectTypeAlias,
    ) -> None:
        """Test mock_update_tags no change."""
        caplog.set_level(LogLevels.DEBUG, logger=MODULE)
        bucket = Bucket(project.ctx, project.args.bucket_name)
        mocker.patch.object(DeploymentPackageS3Object, "bucket", bucket)
        mocker.patch.object(DeploymentPackageS3Object, "object_tags", {"bar": "foo"})
        mock_build_tag_set = mocker.patch.object(
            DeploymentPackageS3Object, "build_tag_set", return_value={"bar": "foo"}
        )
        object_key = mocker.patch.object(DeploymentPackageS3Object, "object_key", "key")
        stubber = cast("Stubber", project.ctx.add_stubber("s3"))  # type: ignore
        with stubber:
            assert not DeploymentPackageS3Object(project).update_tags()
        mock_build_tag_set.assert_called_once_with(url_encoded=False)
        stubber.assert_no_pending_responses()
        assert (
            f"{bucket.format_bucket_path_uri(key=object_key)} tags don't need to be updated"
            in caplog.messages
        )

    @pytest.mark.parametrize("build", [False, True])
    def test_upload_exists(
        self,
        build: bool,
        caplog: LogCaptureFixture,
        mocker: MockerFixture,
        project: ProjectTypeAlias,
    ) -> None:
        """Test upload object exists."""
        caplog.set_level(LogLevels.INFO, logger=MODULE)
        mocker.patch.object(DeploymentPackageS3Object, "exists", True)
        bucket = Bucket(project.ctx, project.args.bucket_name)
        object_key = mocker.patch.object(DeploymentPackageS3Object, "object_key", "key")
        mocker.patch.object(DeploymentPackageS3Object, "bucket", bucket)
        mock_update_tags = mocker.patch.object(DeploymentPackageS3Object, "update_tags")
        assert not DeploymentPackageS3Object(project).upload(build=build)
        assert (
            f"upload skipped; {bucket.format_bucket_path_uri(key=object_key)} already exists"
            in caplog.messages
        )
        mock_update_tags.assert_called_once_with()

    def test_upload_not_exists(self, mocker: MockerFixture, project: ProjectTypeAlias) -> None:
        """Test upload object doesn't exist raises S3ObjectDoesNotExistError."""
        mocker.patch.object(DeploymentPackageS3Object, "exists", False)
        bucket = Bucket(project.ctx, project.args.bucket_name)
        mocker.patch.object(DeploymentPackageS3Object, "bucket", bucket)
        mock_update_tags = mocker.patch.object(DeploymentPackageS3Object, "update_tags")
        obj = DeploymentPackageS3Object(project)
        with pytest.raises(S3ObjectDoesNotExistError) as excinfo:
            obj.upload()
        assert excinfo.value.bucket == bucket.name
        assert excinfo.value.key == obj.object_key
        mock_update_tags.assert_not_called()
