"""Test runway.cfngin.lookups.handlers.awslambda."""
# pylint: disable=no-self-use,redefined-outer-name
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from mock import Mock
from troposphere.awslambda import Code, Content

from runway.cfngin.exceptions import CfnginOnlyLookupError
from runway.cfngin.hooks.awslambda.base_classes import AwsLambdaHook
from runway.cfngin.hooks.awslambda.models.responses import AwsLambdaHookDeployResponse
from runway.cfngin.lookups.handlers.awslambda import AwsLambdaLookup
from runway.config import CfnginConfig
from runway.config.models.cfngin import (
    CfnginConfigDefinitionModel,
    CfnginHookDefinitionModel,
)
from runway.lookups.handlers.base import LookupHandler

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from runway.context import CfnginContext, RunwayContext

MODULE = "runway.cfngin.lookups.handlers.awslambda"
QUERY = "test::foo=bar"


@pytest.fixture(scope="function")
def hook_data() -> AwsLambdaHookDeployResponse:
    """Fixture for hook response data."""
    return AwsLambdaHookDeployResponse(
        code_sha256="code_sha256",
        compatible_architectures=["compatible_architectures"],
        compatible_runtimes=["compatible_runtimes"],
        license="license",
        runtime="runtime",
        bucket_name="bucket_name",
        object_key="object_key",
        object_version_id="object_version_id",
    )


class TestAwsLambdaLookup:
    """Test AwsLambdaLookup."""

    def test_get_deployment_package_data(
        self, hook_data: AwsLambdaHookDeployResponse
    ) -> None:
        """Test get_deployment_package_data."""
        data_key = "test.key"
        assert (
            AwsLambdaLookup.get_deployment_package_data(
                Mock(hook_data={data_key: hook_data.dict(by_alias=True)}), data_key
            )
            == hook_data
        )

    def test_get_deployment_package_data_set_hook_data(
        self,
        cfngin_context: CfnginContext,
        hook_data: AwsLambdaHookDeployResponse,
        mocker: MockerFixture,
    ) -> None:
        """Test get_deployment_package_data set hook_data when it's missing."""
        data_key = "test.key"
        hook = Mock(plan=Mock(return_value=hook_data.dict(by_alias=True)))
        init_hook_class = mocker.patch.object(
            AwsLambdaLookup, "init_hook_class", return_value=hook
        )
        get_required_hook_definition = mocker.patch.object(
            AwsLambdaLookup, "get_required_hook_definition", return_value="hook_def"
        )
        assert (
            AwsLambdaLookup.get_deployment_package_data(cfngin_context, data_key)
            == hook_data
        )
        get_required_hook_definition.assert_called_once_with(
            cfngin_context.config, data_key
        )
        init_hook_class.assert_called_once_with(
            cfngin_context, get_required_hook_definition.return_value
        )
        hook.plan.assert_called_once_with()
        assert cfngin_context.hook_data[data_key] == hook_data.dict(by_alias=True)

    def test_get_deployment_package_data_raise_type_error(self) -> None:
        """Test get_deployment_package_data."""
        with pytest.raises(TypeError) as excinfo:
            assert not AwsLambdaLookup.get_deployment_package_data(
                Mock(hook_data={"test": {"invalid": True}}), "test"
            )
        assert "expected AwsLambdaHookDeployResponseTypedDict, not " in str(
            excinfo.value
        )

    def test_get_required_hook_definition(self) -> None:
        """Test get_required_hook_definition."""
        data_key = "test.data"
        expected_hook = CfnginHookDefinitionModel(data_key=data_key, path="foo.bar")
        config = CfnginConfig(
            CfnginConfigDefinitionModel(
                namespace="test",
                pre_deploy=[
                    expected_hook,
                    CfnginHookDefinitionModel(data_key="foo", path="foo"),
                ],
                pre_destroy=[
                    CfnginHookDefinitionModel(data_key=data_key, path="pre_destroy")
                ],
                post_deploy=[
                    CfnginHookDefinitionModel(data_key=data_key, path="post_deploy")
                ],
                post_destroy=[
                    CfnginHookDefinitionModel(data_key=data_key, path="post_destroy")
                ],
            )
        )
        assert (
            AwsLambdaLookup.get_required_hook_definition(config, data_key)
            == expected_hook
        )

    def test_get_required_hook_definition_raise_value_error_more_than_one(self) -> None:
        """Test get_required_hook_definition raise ValueError for more than one."""
        data_key = "test.data"
        expected_hook = CfnginHookDefinitionModel(data_key=data_key, path="foo.bar")
        config = CfnginConfig(
            CfnginConfigDefinitionModel(
                namespace="test",
                pre_deploy=[expected_hook, expected_hook],
            )
        )
        with pytest.raises(ValueError) as excinfo:
            assert not AwsLambdaLookup.get_required_hook_definition(config, data_key)
        assert (
            str(excinfo.value)
            == f"more than one hook definition found with data_key {data_key}"
        )

    def test_get_required_hook_definition_raise_value_error_none(self) -> None:
        """Test get_required_hook_definition raise ValueError none found."""
        data_key = "test.data"
        config = CfnginConfig(
            CfnginConfigDefinitionModel(
                namespace="test",
                pre_deploy=[
                    CfnginHookDefinitionModel(data_key="foo", path="foo"),
                ],
                pre_destroy=[
                    CfnginHookDefinitionModel(data_key=data_key, path="pre_destroy")
                ],
                post_deploy=[
                    CfnginHookDefinitionModel(data_key=data_key, path="post_deploy")
                ],
                post_destroy=[
                    CfnginHookDefinitionModel(data_key=data_key, path="post_destroy")
                ],
            )
        )
        with pytest.raises(ValueError) as excinfo:
            assert not AwsLambdaLookup.get_required_hook_definition(config, data_key)
        assert (
            str(excinfo.value) == f"no hook definition found with data_key {data_key}"
        )

    def test_handle(self, mocker: MockerFixture) -> None:
        """Test handle."""
        context = Mock()
        mock_format_results = mocker.patch.object(
            LookupHandler, "format_results", return_value="success"
        )
        mock_get_deployment_package_data = mocker.patch.object(
            AwsLambdaLookup, "get_deployment_package_data", return_value="success"
        )
        mock_parse = mocker.patch.object(
            AwsLambdaLookup, "parse", return_value=("query", {})
        )
        assert (
            AwsLambdaLookup.handle(QUERY, context)
            == mock_get_deployment_package_data.return_value
        )
        mock_parse.assert_called_once_with(QUERY)
        mock_get_deployment_package_data.assert_called_once_with(
            context, mock_parse.return_value[0]
        )
        mock_format_results.assert_not_called()

    def test_handle_raise_cfngin_only_lookup_error(
        self, runway_context: RunwayContext
    ) -> None:
        """Test handle raise CfnginOnlyLookupError."""
        with pytest.raises(CfnginOnlyLookupError):
            AwsLambdaLookup.handle("test", runway_context)

    def test_init_hook_class(self, mocker: MockerFixture) -> None:
        """Test init_hook_class."""
        context = Mock()
        hook_class = Mock(return_value="success")
        hook_def = Mock(args={"foo": "var"}, path="foo.bar")
        load_object_from_string = mocker.patch(
            f"{MODULE}.load_object_from_string", return_value=hook_class
        )
        mock_isinstance = mocker.patch(f"{MODULE}.isinstance", return_value=True)
        mock_hasattr = mocker.patch(f"{MODULE}.hasattr", return_value=True)
        mock_issubclass = mocker.patch(f"{MODULE}.issubclass", return_value=True)
        assert (
            AwsLambdaLookup.init_hook_class(context, hook_def)
            == hook_class.return_value
        )
        load_object_from_string.assert_called_once_with(hook_def.path)
        mock_isinstance.assert_called_once_with(hook_class, type)
        mock_hasattr.assert_called_once_with(hook_class, "__subclasscheck__")
        mock_issubclass.assert_called_once_with(hook_class, AwsLambdaHook)
        hook_class.assert_called_once_with(context, **hook_def.args)

    def test_init_hook_class_raise_type_error_not_class(
        self, mocker: MockerFixture
    ) -> None:
        """Test init_hook_class raise TypeError not a class."""

        def _test_func() -> None:
            pass

        context = Mock()
        hook_def = Mock(data_key="test", path="foo.bar")
        mocker.patch(f"{MODULE}.load_object_from_string", return_value=_test_func)
        with pytest.raises(TypeError) as excinfo:
            AwsLambdaLookup.init_hook_class(context, hook_def)
        assert str(excinfo.value) == (
            f"hook path {hook_def.path} for hook with data_key {hook_def.data_key} "
            "must be a subclass of AwsLambdaHook to use this lookup"
        )

    def test_init_hook_class_raise_type_error_not_subclass(
        self, mocker: MockerFixture
    ) -> None:
        """Test init_hook_class raise TypeError not a class."""
        hook_class = Mock(return_value="success")
        context = Mock()
        hook_def = Mock(data_key="test", path="foo.bar")
        mocker.patch(f"{MODULE}.load_object_from_string", return_value=hook_class)
        mocker.patch(f"{MODULE}.hasattr", return_value=True)
        mocker.patch(f"{MODULE}.issubclass", return_value=False)
        with pytest.raises(TypeError) as excinfo:
            AwsLambdaLookup.init_hook_class(context, hook_def)
        assert str(excinfo.value) == (
            f"hook path {hook_def.path} for hook with data_key {hook_def.data_key} "
            "must be a subclass of AwsLambdaHook to use this lookup"
        )


class TestAwsLambdaLookupCode:
    """Test TestAwsLambdaLookup.Code."""

    def test_handle(
        self, hook_data: AwsLambdaHookDeployResponse, mocker: MockerFixture
    ) -> None:
        """Test handle."""
        context = Mock()
        mock_format_results = mocker.patch.object(
            LookupHandler, "format_results", return_value="success"
        )
        mock_handle = mocker.patch.object(
            AwsLambdaLookup, "handle", return_value=hook_data
        )
        result = AwsLambdaLookup.Code.handle(QUERY, context, "arg", foo="bar")
        assert isinstance(result, Code)
        assert not hasattr(result, "ImageUri")
        assert result.S3Bucket == hook_data.bucket_name
        assert result.S3Key == hook_data.object_key
        assert result.S3ObjectVersion == hook_data.object_version_id
        assert not hasattr(result, "ZipFile")
        mock_handle.assert_called_once_with(QUERY, context, "arg", foo="bar")
        mock_format_results.assert_not_called()

    def test_type_name(self) -> None:
        """Test TYPE_NAME."""
        assert (
            AwsLambdaLookup.Code.TYPE_NAME
            == f"{AwsLambdaLookup.TYPE_NAME}.{AwsLambdaLookup.Code.__name__}"
        )


class TestAwsLambdaLookupCodeSha256:
    """Test TestAwsLambdaLookup.CodeSha256."""

    def test_handle(
        self, hook_data: AwsLambdaHookDeployResponse, mocker: MockerFixture
    ) -> None:
        """Test handle."""
        context = Mock()
        mock_format_results = mocker.patch.object(
            LookupHandler, "format_results", return_value="success"
        )
        mock_handle = mocker.patch.object(
            AwsLambdaLookup, "handle", return_value=hook_data
        )
        assert (
            AwsLambdaLookup.CodeSha256.handle(QUERY, context, "arg", foo="bar")
            == hook_data.code_sha256
        )
        mock_handle.assert_called_once_with(QUERY, context, "arg", foo="bar")
        mock_format_results.assert_not_called()

    def test_type_name(self) -> None:
        """Test TYPE_NAME."""
        assert (
            AwsLambdaLookup.CodeSha256.TYPE_NAME
            == f"{AwsLambdaLookup.TYPE_NAME}.{AwsLambdaLookup.CodeSha256.__name__}"
        )


class TestAwsLambdaLookupCompatibleArchitectures:
    """Test TestAwsLambdaLookup.CompatibleArchitectures."""

    def test_handle(
        self, hook_data: AwsLambdaHookDeployResponse, mocker: MockerFixture
    ) -> None:
        """Test handle."""
        context = Mock()
        mock_format_results = mocker.patch.object(
            LookupHandler, "format_results", return_value="success"
        )
        mock_handle = mocker.patch.object(
            AwsLambdaLookup, "handle", return_value=hook_data
        )
        assert (
            AwsLambdaLookup.CompatibleArchitectures.handle(
                QUERY, context, "arg", foo="bar"
            )
            == mock_format_results.return_value
        )
        mock_handle.assert_called_once_with(QUERY, context, "arg", foo="bar")
        mock_format_results.assert_called_once_with(
            hook_data.compatible_architectures, foo="bar"
        )

    def test_type_name(self) -> None:
        """Test TYPE_NAME."""
        assert (
            AwsLambdaLookup.CompatibleArchitectures.TYPE_NAME
            == f"{AwsLambdaLookup.TYPE_NAME}.{AwsLambdaLookup.CompatibleArchitectures.__name__}"
        )


class TestAwsLambdaLookupCompatibleRuntimes:
    """Test TestAwsLambdaLookup.CompatibleRuntimes."""

    def test_handle(
        self, hook_data: AwsLambdaHookDeployResponse, mocker: MockerFixture
    ) -> None:
        """Test handle."""
        context = Mock()
        mock_format_results = mocker.patch.object(
            LookupHandler, "format_results", return_value="success"
        )
        mock_handle = mocker.patch.object(
            AwsLambdaLookup, "handle", return_value=hook_data
        )
        assert (
            AwsLambdaLookup.CompatibleRuntimes.handle(QUERY, context, "arg", foo="bar")
            == mock_format_results.return_value
        )
        mock_handle.assert_called_once_with(QUERY, context, "arg", foo="bar")
        mock_format_results.assert_called_once_with(
            hook_data.compatible_runtimes, foo="bar"
        )

    def test_type_name(self) -> None:
        """Test TYPE_NAME."""
        assert (
            AwsLambdaLookup.CompatibleRuntimes.TYPE_NAME
            == f"{AwsLambdaLookup.TYPE_NAME}.{AwsLambdaLookup.CompatibleRuntimes.__name__}"
        )


class TestAwsLambdaLookupContent:
    """Test TestAwsLambdaLookup.Content."""

    def test_handle(
        self, hook_data: AwsLambdaHookDeployResponse, mocker: MockerFixture
    ) -> None:
        """Test handle."""
        context = Mock()
        mock_format_results = mocker.patch.object(
            LookupHandler, "format_results", return_value="success"
        )
        mock_handle = mocker.patch.object(
            AwsLambdaLookup, "handle", return_value=hook_data
        )
        result = AwsLambdaLookup.Content.handle(QUERY, context, "arg", foo="bar")
        assert isinstance(result, Content)
        assert not hasattr(result, "ImageUri")
        assert result.S3Bucket == hook_data.bucket_name
        assert result.S3Key == hook_data.object_key
        assert result.S3ObjectVersion == hook_data.object_version_id
        mock_handle.assert_called_once_with(QUERY, context, "arg", foo="bar")
        mock_format_results.assert_not_called()

    def test_type_name(self) -> None:
        """Test TYPE_NAME."""
        assert (
            AwsLambdaLookup.Content.TYPE_NAME
            == f"{AwsLambdaLookup.TYPE_NAME}.{AwsLambdaLookup.Content.__name__}"
        )


class TestAwsLambdaLookupLicenseInfo:
    """Test TestAwsLambdaLookup.LicenseInfo."""

    def test_handle(
        self, hook_data: AwsLambdaHookDeployResponse, mocker: MockerFixture
    ) -> None:
        """Test handle."""
        context = Mock()
        mock_format_results = mocker.patch.object(
            LookupHandler, "format_results", return_value="success"
        )
        mock_handle = mocker.patch.object(
            AwsLambdaLookup, "handle", return_value=hook_data
        )
        assert (
            AwsLambdaLookup.LicenseInfo.handle(QUERY, context, "arg", foo="bar")
            == mock_format_results.return_value
        )
        mock_handle.assert_called_once_with(QUERY, context, "arg", foo="bar")
        mock_format_results.assert_called_once_with(hook_data.license, foo="bar")

    def test_type_name(self) -> None:
        """Test TYPE_NAME."""
        assert (
            AwsLambdaLookup.LicenseInfo.TYPE_NAME
            == f"{AwsLambdaLookup.TYPE_NAME}.{AwsLambdaLookup.LicenseInfo.__name__}"
        )


class TestAwsLambdaLookupRuntime:
    """Test TestAwsLambdaLookup.Runtime."""

    def test_handle(
        self, hook_data: AwsLambdaHookDeployResponse, mocker: MockerFixture
    ) -> None:
        """Test handle."""
        context = Mock()
        mock_format_results = mocker.patch.object(
            LookupHandler, "format_results", return_value="success"
        )
        mock_handle = mocker.patch.object(
            AwsLambdaLookup, "handle", return_value=hook_data
        )
        assert (
            AwsLambdaLookup.Runtime.handle(QUERY, context, "arg", foo="bar")
            == hook_data.runtime
        )
        mock_handle.assert_called_once_with(QUERY, context, "arg", foo="bar")
        mock_format_results.assert_not_called()

    def test_type_name(self) -> None:
        """Test TYPE_NAME."""
        assert (
            AwsLambdaLookup.Runtime.TYPE_NAME
            == f"{AwsLambdaLookup.TYPE_NAME}.{AwsLambdaLookup.Runtime.__name__}"
        )


class TestAwsLambdaLookupS3Bucket:
    """Test TestAwsLambdaLookup.S3Bucket."""

    def test_handle(
        self, hook_data: AwsLambdaHookDeployResponse, mocker: MockerFixture
    ) -> None:
        """Test handle."""
        context = Mock()
        mock_format_results = mocker.patch.object(
            LookupHandler, "format_results", return_value="success"
        )
        mock_handle = mocker.patch.object(
            AwsLambdaLookup, "handle", return_value=hook_data
        )
        assert (
            AwsLambdaLookup.S3Bucket.handle(QUERY, context, "arg", foo="bar")
            == hook_data.bucket_name
        )
        mock_handle.assert_called_once_with(QUERY, context, "arg", foo="bar")
        mock_format_results.assert_not_called()

    def test_type_name(self) -> None:
        """Test TYPE_NAME."""
        assert (
            AwsLambdaLookup.S3Bucket.TYPE_NAME
            == f"{AwsLambdaLookup.TYPE_NAME}.{AwsLambdaLookup.S3Bucket.__name__}"
        )


class TestAwsLambdaLookupS3Key:
    """Test TestAwsLambdaLookup.S3Key."""

    def test_handle(
        self, hook_data: AwsLambdaHookDeployResponse, mocker: MockerFixture
    ) -> None:
        """Test handle."""
        context = Mock()
        mock_format_results = mocker.patch.object(
            LookupHandler, "format_results", return_value="success"
        )
        mock_handle = mocker.patch.object(
            AwsLambdaLookup, "handle", return_value=hook_data
        )
        assert (
            AwsLambdaLookup.S3Key.handle(QUERY, context, "arg", foo="bar")
            == hook_data.object_key
        )
        mock_handle.assert_called_once_with(QUERY, context, "arg", foo="bar")
        mock_format_results.assert_not_called()

    def test_type_name(self) -> None:
        """Test TYPE_NAME."""
        assert (
            AwsLambdaLookup.S3Key.TYPE_NAME
            == f"{AwsLambdaLookup.TYPE_NAME}.{AwsLambdaLookup.S3Key.__name__}"
        )


class TestAwsLambdaLookupS3ObjectVersion:
    """Test TestAwsLambdaLookup.S3ObjectVersion."""

    def test_handle(
        self, hook_data: AwsLambdaHookDeployResponse, mocker: MockerFixture
    ) -> None:
        """Test handle."""
        context = Mock()
        mock_format_results = mocker.patch.object(
            LookupHandler, "format_results", return_value="success"
        )
        mock_handle = mocker.patch.object(
            AwsLambdaLookup, "handle", return_value=hook_data
        )
        assert (
            AwsLambdaLookup.S3ObjectVersion.handle(QUERY, context, "arg", foo="bar")
            == hook_data.object_version_id
        )
        mock_handle.assert_called_once_with(QUERY, context, "arg", foo="bar")
        mock_format_results.assert_not_called()

    def test_type_name(self) -> None:
        """Test TYPE_NAME."""
        assert (
            AwsLambdaLookup.S3ObjectVersion.TYPE_NAME
            == f"{AwsLambdaLookup.TYPE_NAME}.{AwsLambdaLookup.S3ObjectVersion.__name__}"
        )
