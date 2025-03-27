"""Test classes."""

# pyright: reportIncompatibleMethodOverride=none
from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import MagicMock

import boto3
import yaml
from botocore.stub import Stubber
from packaging.specifiers import SpecifierSet

from runway.config.components.runway import RunwayDeploymentDefinition
from runway.context import CfnginContext, RunwayContext
from runway.utils import MutableMap

if TYPE_CHECKING:
    from collections.abc import MutableMapping
    from pathlib import Path

    from boto3.resources.base import ServiceResource
    from botocore.client import BaseClient
    from mypy_boto3_s3.client import S3Client

    from runway.config import CfnginConfig
    from runway.core.components import DeployEnvironment
    from runway.core.type_defs import RunwayActionTypeDef


class MockBoto3Session:
    """Mock class that acts like a :class:`boto3.session.Session`.

    Clients must be registered using :meth:`~pytest_runway.MockBoto3Session.register_client`
    before the can be created with the usual :meth:`~pytest_runway.MockBoto3Session.client`
    call. This is to ensure that all AWS calls are stubbed.

    """

    def __init__(
        self,
        *,
        clients: MutableMap | None = None,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        aws_session_token: str | None = None,
        profile_name: str | None = None,
        region_name: str | None = None,
    ) -> None:
        """Instantiate class.

        Args:
            clients: Clients that have already been stubbed.
            aws_access_key_id: Same as boto3.Session.
            aws_secret_access_key: Same as boto3.Session.
            aws_session_token: Same as boto3.Session.
            profile_name: Same as boto3.Session.
            region_name: Same as boto3.Session.

        """
        self._clients = clients or MutableMap()
        self._session = MagicMock()
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_session_token = aws_session_token
        self.profile_name = profile_name
        self.region_name = region_name

    def client(self, service_name: str, **kwargs: Any) -> BaseClient:
        """Return a stubbed client.

        Args:
            service_name: The name of a service, e.g. 's3' or 'ec2'.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Stubbed boto3 client.

        Raises:
            ValueError: Client was not stubbed from Context before trying to use.

        """
        key = f"{service_name}.{kwargs.get('region_name') or self.region_name}"
        try:
            return self._clients[key]
        except AttributeError:
            raise ValueError(f"client not registered for {key}") from None

    def register_client(
        self, service_name: str, *, region: str | None = None
    ) -> tuple[Any, Stubber]:
        """Register a client for the boto3 session.

        Args:
            service_name: The name of a service, e.g. 's3' or 'ec2'.
            region: AWS region.

        """
        key = f"{service_name}.{region or self.region_name}"
        client = cast(
            "BaseClient",
            boto3.client(
                service_name,  # pyright: ignore[reportCallIssue, reportArgumentType]
                region_name=region or self.region_name,
            ),
        )
        stubber = Stubber(client)
        self._clients[key] = client
        return client, stubber

    def resource(self, service_name: str, **kwargs: Any) -> ServiceResource:
        """Return a stubbed resource."""
        kwargs.setdefault("region_name", self.region_name)
        resource = cast(
            "ServiceResource",
            boto3.resource(
                service_name,  # pyright: ignore[reportCallIssue, reportArgumentType]
                **kwargs,
            ),
        )
        resource.meta.client = self.client(service_name, **kwargs)
        return resource

    def service(self, service_name: str, *, region_name: str | None = None) -> None:
        """Not implemented."""
        raise NotImplementedError


class MockCfnginContext(CfnginContext):
    """Subclass of :class:`~runway.context.CfnginContext` for tests."""

    def __init__(
        self,
        *,
        config: CfnginConfig | None = None,
        config_path: Path | None = None,
        deploy_environment: DeployEnvironment,
        force_stacks: list[str] | None = None,
        parameters: MutableMapping[str, Any] | None = None,
        stack_names: list[str] | None = None,
        work_dir: Path | None = None,
        **_: Any,
    ) -> None:
        """Instantiate class.

        Args:
            config: The CFNgin configuration being operated on.
            config_path: Path to the config file that was provided.
            deploy_environment: The current deploy environment.
            force_stacks: A list of stacks to force work on. Used to work on locked stacks.
            parameters: Parameters passed from Runway or read from a file.
            stack_names: A list of stack_names to operate on. If not passed,
                all stacks defined in the config will be operated on.
            work_dir: Working directory used by CFNgin.

        """
        self._boto3_sessions: dict[str, MockBoto3Session] = {}

        super().__init__(
            config_path=config_path,
            config=config,
            deploy_environment=deploy_environment,
            force_stacks=force_stacks,
            parameters=parameters,
            stack_names=stack_names,
            work_dir=work_dir,
        )

    @cached_property
    def s3_client(self) -> S3Client:
        """AWS S3 client.

        Adds an S3 stubber prior to returning from :attr:`~runway.context.CfnginContext.s3_client`.

        """
        self.add_stubber("s3", region=self.bucket_region)
        return super().s3_client

    def add_stubber(
        self,
        service_name: str,
        *,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        aws_session_token: str | None = None,
        profile: str | None = None,
        region: str | None = None,
    ) -> Stubber:
        """Add a stubber to context.

        Args:
            service_name: The name of the service to stub.
            aws_access_key_id: AWS Access Key ID.
            aws_secret_access_key: AWS secret Access Key.
            aws_session_token: AWS session token.
            profile: The profile for the session.
            region: The region for the session.

        """
        session = self._get_mocked_session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
            profile=profile,
            region=region or self.env.aws_region,
        )
        _client, stubber = session.register_client(service_name, region=region)
        return stubber

    def _get_mocked_session(
        self,
        *,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        aws_session_token: str | None = None,
        profile: str | None = None,
        region: str | None = None,
    ) -> MockBoto3Session:
        """Get a mocked boto3 session."""
        region = region or self.env.aws_region
        if region not in self._boto3_sessions:
            self._boto3_sessions[region] = MockBoto3Session(
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                aws_session_token=aws_session_token,
                profile_name=profile,
                region_name=region or self.env.aws_region,
            )
        return self._boto3_sessions[region]

    def get_session(
        self,
        *,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        aws_session_token: str | None = None,
        profile: str | None = None,
        region: str | None = None,
    ) -> boto3.Session:
        """Wrap get_session to enable stubbing.

        A stubber must exist before ``get_session`` is called or an error will be raised.

        Args:
            aws_access_key_id: AWS Access Key ID.
            aws_secret_access_key: AWS secret Access Key.
            aws_session_token: AWS session token.
            profile: The profile for the session.
            region: The region for the session.

        """
        return cast(
            "boto3.Session",
            self._get_mocked_session(
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                aws_session_token=aws_session_token,
                profile=profile,
                region=region or self.env.aws_region,
            ),
        )

    def get_stubbed_client(self, service_name: str, *, region: str | None = None) -> BaseClient:
        """Get an existing stubbed client.

        This can be used after :meth:`~pytest_runway.MockCfnginContext.add_stubber` has
        been called to get the stubber client.

        Args:
            service_name: The name of the service that was stubbed.
            region: The region of the session.

        """
        return self._get_mocked_session(region=region).client(service_name, region_name=region)


class MockRunwayConfig(MutableMap):
    """Mock Runway config object."""

    def __init__(self, **kwargs: Any) -> None:
        """Instantiate class."""
        super().__init__()
        self._kwargs = kwargs
        self.deployments = []
        self.future = MagicMock()
        self.tests = []
        self.ignore_git_branch = False
        self.runway_version = SpecifierSet(">=0.0.0", prereleases=True)
        self.variables = MutableMap()

        # classmethods
        self.find_config_file = MagicMock(name="find_config_file", return_value="./runway.yml")
        self.load_from_file = MagicMock(name="load_from_file", return_value=self)

    def __call__(self, **kwargs: Any) -> MockRunwayConfig:
        """Mock call to return self."""
        self._kwargs = kwargs
        return self


class MockRunwayContext(RunwayContext):
    """Subclass of :class:`~runway.context.RunwayContext` for tests."""

    _use_concurrent: bool = True

    def __init__(
        self,
        *,
        command: RunwayActionTypeDef | None = None,
        deploy_environment: DeployEnvironment,
        work_dir: Path | None = None,
        **_: Any,
    ) -> None:
        """Instantiate class.

        Args:
            command: Runway command/action being run.
            deploy_environment: The current deploy environment.
            work_dir: Working directory used by Runway.

        """
        self._boto3_sessions: dict[str, MockBoto3Session] = {}

        super().__init__(command=command, deploy_environment=deploy_environment, work_dir=work_dir)

    @property
    def use_concurrent(self) -> bool:
        """Override property of parent with something that can be set."""
        return self._use_concurrent

    @use_concurrent.setter
    def use_concurrent(  # pyright: ignore[reportIncompatibleVariableOverride]
        self, value: bool
    ) -> None:
        """Override property of parent with something that can be set.

        Args:
            value: New value for the attribute.

        """
        self._use_concurrent = value

    def add_stubber(
        self,
        service_name: str,
        *,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        aws_session_token: str | None = None,
        profile: str | None = None,
        region: str | None = None,
    ) -> Stubber:
        """Add a stubber to context.

        Args:
            service_name: The name of the service to stub.
            aws_access_key_id: AWS Access Key ID.
            aws_secret_access_key: AWS secret Access Key.
            aws_session_token: AWS session token.
            profile: The profile for the session.
            region: The region for the session.

        """
        session = self._get_mocked_session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
            profile=profile,
            region=region or self.env.aws_region,
        )
        _client, stubber = session.register_client(service_name, region=region)
        return stubber

    def _get_mocked_session(
        self,
        *,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        aws_session_token: str | None = None,
        profile: str | None = None,
        region: str | None = None,
    ) -> MockBoto3Session:
        """Get a mocked boto3 session."""
        region = region or self.env.aws_region
        if region not in self._boto3_sessions:
            self._boto3_sessions[region] = MockBoto3Session(
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                aws_session_token=aws_session_token,
                profile_name=profile,
                region_name=region or self.env.aws_region,
            )
        return self._boto3_sessions[region]

    def get_session(
        self,
        *,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        aws_session_token: str | None = None,
        profile: str | None = None,
        region: str | None = None,
    ) -> boto3.Session:
        """Wrap get_session to enable stubbing.

        A stubber must exist before ``get_session`` is called or an error will be raised.

        Args:
            aws_access_key_id: AWS Access Key ID.
            aws_secret_access_key: AWS secret Access Key.
            aws_session_token: AWS session token.
            profile: The profile for the session.
            region: The region for the session.

        """
        return cast(
            "boto3.Session",
            self._get_mocked_session(
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                aws_session_token=aws_session_token,
                profile=profile,
                region=region or self.env.aws_region,
            ),
        )

    def get_stubbed_client(self, service_name: str, *, region: str | None = None) -> BaseClient:
        """Get an existing stubbed client.

        This can be used after :meth:`~pytest_runway.MockCfnginContext.add_stubber` has
        been called to get the stubber client.

        Args:
            service_name: The name of the service that was stubbed.
            region: The region of the session.

        """
        return self._get_mocked_session(region=region).client(service_name, region_name=region)


class YamlLoader:
    """Load YAML files from a directory."""

    def __init__(
        self, root: Path, load_class: type | None = None, load_type: str = "default"
    ) -> None:
        """Instantiate class.

        Args:
            root: Root directory.
            load_class: Class to use with load method.
            load_type: Controls how content is passed to the load_class.

        """
        self.load_class = load_class
        self.load_type = load_type
        root.absolute()
        self.root = root

    def get(self, file_name: str) -> Any:
        """Get raw YAML file contents.

        Args:
            file_name: Name of the file to load.

        Returns:
            Content of the file loaded by PyYAML.

        """
        if not file_name.endswith(".yml") or not file_name.endswith(".yaml"):
            file_name += ".yml"
        content = (self.root / file_name).read_text()
        return yaml.safe_load(content)

    def load(self, file_name: str) -> Any:
        """Load YAML file contents.

        Args:
            file_name (str): Name of the file to load.

        Returns:
            Any

        """
        if not self.load_class:
            raise ValueError("load_class must be set to use this method")
        if self.load_type == "default":
            return self.load_class(self.get(file_name))
        if self.load_type == "kwargs":
            return self.load_class(**self.get(file_name))
        raise ValueError(f'invalid load_type; "{self.load_type}"')


class YamlLoaderDeployment(YamlLoader):
    """Load deployment YAML files from a directory."""

    def __init__(self, root: Path) -> None:
        """Instantiate class.

        Args:
            root: Root directory.

        """
        super().__init__(root, load_class=RunwayDeploymentDefinition)

    def load(self, file_name: str) -> RunwayDeploymentDefinition:
        """Load YAML file contents.

        Args:
            file_name: Name of the file to load.

        """
        return self.load_class.parse_obj(self.get(file_name))  # type: ignore
