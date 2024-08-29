"""Dedicated lookup for use with :class:`~runway.cfngin.hooks.awslambda.base_classes.AwsLambdaHook` based hooks.

To use this hook, there must be a
:class:`~runway.cfngin.hooks.awslambda.base_classes.AwsLambdaHook` based hook defined
in the :attr:`~cfngin.config.pre_deploy` section of the CFNgin configuration file.
This hook must also define a :attr:`~cfngin.hook.data_key` that is unique within
the CFNgin configuration file (it can be reused in other CFNgin configuration files).
The :attr:`~cfngin.hook.data_key` is then passed to the lookup as it's input/query.
This allows the lookup to function during a ``runway plan``.

"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar, cast

from pydantic import ValidationError
from troposphere.awslambda import Code, Content

from ....lookups.handlers.base import LookupHandler
from ....utils import load_object_from_string

if TYPE_CHECKING:

    from ....config import CfnginConfig
    from ....config.models.cfngin import CfnginHookDefinitionModel
    from ....context import CfnginContext
    from ...hooks.awslambda.base_classes import AwsLambdaHook
    from ...hooks.awslambda.models.responses import AwsLambdaHookDeployResponse

LOGGER = logging.getLogger(__name__)


class AwsLambdaLookup(LookupHandler["CfnginContext"]):
    """Lookup for AwsLambdaHook responses."""

    TYPE_NAME: ClassVar[str] = "awslambda"

    @classmethod
    def get_deployment_package_data(
        cls, context: CfnginContext, data_key: str
    ) -> AwsLambdaHookDeployResponse:
        """Get the response of an AwsLambdaHook run.

        Args:
            context: CFNgin context object.
            data_key: The value of the ``data_key`` field as assigned in a
                Hook definition.

        Returns:
            The :class:`~runway.cfngin.hooks.awslambda.base_classes.AwsLambdaHook`
            response parsed into a data model.
            This will come from hook data if it exists or it will be calculated
            and added to hook data for future use.

        Raises:
            TypeError: The data stored in hook data does not align with the
                expected data model.

        """
        # needs to be imported here to avoid cyclic imports for conditional code
        # caused by import of runway.cfngin.actions.deploy in runway.cfngin.hooks.base
        from ...hooks.awslambda.models.responses import (
            AwsLambdaHookDeployResponse as _AwsLambdaHookDeployResponse,
        )

        if data_key not in context.hook_data:
            LOGGER.debug("%s missing from hook_data; attempting to get value", data_key)
            hook = cls.init_hook_class(
                context, cls.get_required_hook_definition(context.config, data_key)
            )
            context.set_hook_data(data_key, hook.plan())
        try:
            return _AwsLambdaHookDeployResponse.model_validate(context.hook_data[data_key])
        except ValidationError:
            raise TypeError(
                "expected AwsLambdaHookDeployResponseTypedDict, "
                f"not {context.hook_data[data_key]}"
            ) from None

    @staticmethod
    def get_required_hook_definition(
        config: CfnginConfig, data_key: str
    ) -> CfnginHookDefinitionModel:
        """Get the required Hook definition from the CFNgin config.

        Currently, this only supports finding the data_key pre_deploy.

        Args:
            config: CFNgin config being processed.
            data_key: The value of the ``data_key`` field as assigned in a
                Hook definition.

        Returns:
            The Hook definition set to use the provided ``data_key``.

        Raises:
            ValueError: Either a Hook definition was not found for the provided
                ``data_key`` or, more than one was found.

        """
        hooks_with_data_key = [
            hook_def for hook_def in config.pre_deploy if hook_def.data_key == data_key
        ]
        if not hooks_with_data_key:
            raise ValueError(f"no hook definition found with data_key {data_key}")
        if len(hooks_with_data_key) > 1:
            raise ValueError(f"more than one hook definition found with data_key {data_key}")
        return hooks_with_data_key.pop()

    @classmethod
    def handle(
        cls, value: str, context: CfnginContext, **_kwargs: Any
    ) -> AwsLambdaHookDeployResponse:
        """Retrieve metadata for an AWS Lambda deployment package.

        Args:
            value: Value to resolve.
            context: The current context object.

        Returns:
            The full :class:`~awslambda.models.response.AwsLambdaHookDeployResponse`
            data model.

        """
        query, _ = cls.parse(value)
        return cls.get_deployment_package_data(context, query)

    @staticmethod
    def init_hook_class(
        context: CfnginContext, hook_def: CfnginHookDefinitionModel
    ) -> AwsLambdaHook[Any]:
        """Initialize AwsLambdaHook subclass instance.

        Args:
            context: CFNgin context object.
            hook_def: The :class:`~runway.cfngin.hooks.awslambda.base_classes.AwsLambdaHook`
                definition.

        Returns:
            The loaded AwsLambdaHook object.

        """
        # needs to be imported here to avoid cyclic imports for conditional code
        # caused by import of runway.cfngin.actions.deploy in runway.cfngin.hooks.base
        from ...hooks.awslambda.base_classes import AwsLambdaHook as _AwsLambdaHook

        kls = load_object_from_string(hook_def.path)
        if (
            not isinstance(kls, type)
            or not hasattr(kls, "__subclasscheck__")
            or not issubclass(kls, _AwsLambdaHook)
        ):
            raise TypeError(
                f"hook path {hook_def.path} for hook with data_key {hook_def.data_key} "
                "must be a subclass of AwsLambdaHook to use this lookup"
            )
        return cast("AwsLambdaHook[Any]", kls(context, **hook_def.args))

    class Code(LookupHandler["CfnginContext"]):
        """Lookup for AwsLambdaHook responses."""

        TYPE_NAME: ClassVar[str] = "awslambda.Code"

        @classmethod
        def handle(cls, value: str, context: CfnginContext, *args: Any, **kwargs: Any) -> Code:
            """Retrieve metadata for an AWS Lambda deployment package.

            Args:
                value: Value to resolve.
                context: The current context object.
                *args: Variable length argument list.
                **kwargs: Arbitrary keyword arguments.

            Returns:
                Value that can be passed into CloudFormation property
                ``AWS::Lambda::Function.Code``.

            """
            return Code(
                **AwsLambdaLookup.handle(value, context, *args, **kwargs).model_dump(
                    by_alias=True,
                    exclude_none=True,
                    include={"bucket_name", "object_key", "object_version_id"},
                )
            )

    class CodeSha256(LookupHandler["CfnginContext"]):
        """Lookup for AwsLambdaHook responses."""

        TYPE_NAME: ClassVar[str] = "awslambda.CodeSha256"

        @classmethod
        def handle(cls, value: str, context: CfnginContext, *args: Any, **kwargs: Any) -> str:
            """Retrieve metadata for an AWS Lambda deployment package.

            Args:
                value: Value to resolve.
                context: The current context object.
                *args: Variable length argument list.
                **kwargs: Arbitrary keyword arguments.

            Returns:
                Value that can be passed into CloudFormation property
                ``AWS::Lambda::Version.CodeSha256``.

            """
            return AwsLambdaLookup.handle(value, context, *args, **kwargs).code_sha256

    class CompatibleArchitectures(LookupHandler["CfnginContext"]):
        """Lookup for AwsLambdaHook responses."""

        TYPE_NAME: ClassVar[str] = "awslambda.CompatibleArchitectures"

        @classmethod
        def handle(
            cls, value: str, context: CfnginContext, *args: Any, **kwargs: Any
        ) -> list[str] | None:
            """Retrieve metadata for an AWS Lambda deployment package.

            Args:
                value: Value to resolve.
                context: The current context object.
                *args: Variable length argument list.
                **kwargs: Arbitrary keyword arguments.

            Returns:
                Value that can be passed into CloudFormation property
                ``AWS::Lambda::LayerVersion.CompatibleArchitectures``.

            """
            _query, lookup_args = cls.parse(value)
            return cls.format_results(
                AwsLambdaLookup.handle(value, context, *args, **kwargs).compatible_architectures,
                **lookup_args,
            )

    class CompatibleRuntimes(LookupHandler["CfnginContext"]):
        """Lookup for AwsLambdaHook responses."""

        TYPE_NAME: ClassVar[str] = "awslambda.CompatibleRuntimes"

        @classmethod
        def handle(cls, value: str, context: CfnginContext, *args: Any, **kwargs: Any) -> Any:
            """Retrieve metadata for an AWS Lambda deployment package.

            Args:
                value: Value to resolve.
                context: The current context object.
                *args: Variable length argument list.
                **kwargs: Arbitrary keyword arguments.

            Returns:
                Value that can be passed into CloudFormation property
                ``AWS::Lambda::LayerVersion.CompatibleRuntimes``.

            """
            _query, lookup_args = cls.parse(value)
            return cls.format_results(
                AwsLambdaLookup.handle(value, context, *args, **kwargs).compatible_runtimes,
                **lookup_args,
            )

    class Content(LookupHandler["CfnginContext"]):
        """Lookup for AwsLambdaHook responses."""

        TYPE_NAME: ClassVar[str] = "awslambda.Content"

        @classmethod
        def handle(cls, value: str, context: CfnginContext, *args: Any, **kwargs: Any) -> Content:
            """Retrieve metadata for an AWS Lambda deployment package.

            Args:
                value: Value to resolve.
                context: The current context object.
                *args: Variable length argument list.
                **kwargs: Arbitrary keyword arguments.

            Returns:
                Value that can be passed into CloudFormation property
                ``AWS::Lambda::LayerVersion.Content``.

            """
            return Content(
                **AwsLambdaLookup.handle(value, context, *args, **kwargs).model_dump(
                    by_alias=True,
                    exclude_none=True,
                    include={"bucket_name", "object_key", "object_version_id"},
                )
            )

    class LicenseInfo(LookupHandler["CfnginContext"]):
        """Lookup for AwsLambdaHook responses."""

        TYPE_NAME: ClassVar[str] = "awslambda.LicenseInfo"

        @classmethod
        def handle(
            cls, value: str, context: CfnginContext, *args: Any, **kwargs: Any
        ) -> str | None:
            """Retrieve metadata for an AWS Lambda deployment package.

            Args:
                value: Value to resolve.
                context: The current context object.
                *args: Variable length argument list.
                **kwargs: Arbitrary keyword arguments.

            Returns:
                Value that can be passed into CloudFormation property
                ``AWS::Lambda::LayerVersion.LicenseInfo``.

            """
            _query, lookup_args = cls.parse(value)
            return cls.format_results(
                AwsLambdaLookup.handle(value, context, *args, **kwargs).license,
                **lookup_args,
            )

    class Runtime(LookupHandler["CfnginContext"]):
        """Lookup for AwsLambdaHook responses."""

        TYPE_NAME: ClassVar[str] = "awslambda.Runtime"

        @classmethod
        def handle(cls, value: str, context: CfnginContext, *args: Any, **kwargs: Any) -> str:
            """Retrieve metadata for an AWS Lambda deployment package.

            Args:
                value: Value to resolve.
                context: The current context object.
                *args: Variable length argument list.
                **kwargs: Arbitrary keyword arguments.

            Returns:
                Value that can be passed into CloudFormation property
                ``AWS::Lambda::Function.Runtime``.

            """
            return AwsLambdaLookup.handle(value, context, *args, **kwargs).runtime

    class S3Bucket(LookupHandler["CfnginContext"]):
        """Lookup for AwsLambdaHook responses."""

        TYPE_NAME: ClassVar[str] = "awslambda.S3Bucket"

        @classmethod
        def handle(cls, value: str, context: CfnginContext, *args: Any, **kwargs: Any) -> str:
            """Retrieve metadata for an AWS Lambda deployment package.

            Args:
                value: Value to resolve.
                context: The current context object.
                *args: Variable length argument list.
                **kwargs: Arbitrary keyword arguments.

            Returns:
                Value that can be passed into CloudFormation property
                ``AWS::Lambda::Function.Code.S3Bucket`` or
                ``AWS::Lambda::LayerVersion.Content.S3Bucket``.

            """
            return AwsLambdaLookup.handle(value, context, *args, **kwargs).bucket_name

    class S3Key(LookupHandler["CfnginContext"]):
        """Lookup for AwsLambdaHook responses."""

        TYPE_NAME: ClassVar[str] = "awslambda.S3Key"

        @classmethod
        def handle(cls, value: str, context: CfnginContext, *args: Any, **kwargs: Any) -> str:
            """Retrieve metadata for an AWS Lambda deployment package.

            Args:
                value: Value to resolve.
                context: The current context object.
                *args: Variable length argument list.
                **kwargs: Arbitrary keyword arguments.

            Returns:
                Value that can be passed into CloudFormation property
                ``AWS::Lambda::Function.Code.S3Key`` or
                ``AWS::Lambda::LayerVersion.Content.S3Key``.

            """
            return AwsLambdaLookup.handle(value, context, *args, **kwargs).object_key

    class S3ObjectVersion(LookupHandler["CfnginContext"]):
        """Lookup for AwsLambdaHook responses."""

        TYPE_NAME: ClassVar[str] = "awslambda.S3ObjectVersion"

        @classmethod
        def handle(
            cls, value: str, context: CfnginContext, *args: Any, **kwargs: Any
        ) -> str | None:
            """Retrieve metadata for an AWS Lambda deployment package.

            Args:
                value: Value to resolve.
                context: The current context object.
                *args: Variable length argument list.
                **kwargs: Arbitrary keyword arguments.

            Returns:
                Value that can be passed into CloudFormation property
                ``AWS::Lambda::Function.Code.S3ObjectVersion`` or
                ``AWS::Lambda::LayerVersion.Content.S3ObjectVersion``.

            """
            return AwsLambdaLookup.handle(value, context, *args, **kwargs).object_version_id
