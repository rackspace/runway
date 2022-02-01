"""Test classes."""
# pyright: basic, reportIncompatibleMethodOverride=none
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, MutableMapping, Optional, Tuple

import boto3
import yaml
from botocore.stub import Stubber
from mock import MagicMock
from packaging.specifiers import SpecifierSet

from runway.config.components.runway import RunwayDeploymentDefinition
from runway.context import CfnginContext, RunwayContext
from runway.core.components import DeployEnvironment
from runway.utils import MutableMap

if TYPE_CHECKING:
    from pathlib import Path

    from boto3.resources.base import ServiceResource
    from botocore.client import BaseClient

    from runway.config import CfnginConfig
    from runway.core.type_defs import RunwayActionTypeDef


class MockBoto3Session:
    """Mock class that acts like a boto3.session.

    Must be preloaded with stubbers.

    """

    def __init__(
        self,
        *,
        clients: Optional[MutableMap] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_session_token: Optional[str] = None,
        profile_name: Optional[str] = None,
        region_name: Optional[str] = None,
    ):
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
        self._client_calls: Dict[str, Any] = {}
        self._session = MagicMock()
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_session_token = aws_session_token
        self.profile_name = profile_name
        self.region_name = region_name

    def assert_client_called_with(self, service_name: str, **kwargs: Any) -> None:
        """Assert a client was created with the provided kwargs."""
        key = f"{service_name}.{kwargs.get('region_name', self.region_name)}"
        assert self._client_calls[key] == kwargs

    def client(self, service_name: str, **kwargs: Any) -> BaseClient:
        """Return a stubbed client.

        Args:
            service_name: The name of a service, e.g. 's3' or 'ec2'.

        Returns:
            Stubbed boto3 client.

        Raises:
            KeyError: Client was not stubbed from Context before trying to use.

        """
        key = f"{service_name}.{kwargs.get('region_name', self.region_name)}"
        self._client_calls[key] = kwargs
        return self._clients[key]

    def register_client(
        self, service_name: str, region_name: Optional[str] = None
    ) -> Tuple[Any, Stubber]:
        """Register a client for the boto3 session.

        Args:
            service_name: The name of a service, e.g. 's3' or 'ec2'.
            region_name: AWS region.

        """
        key = f"{service_name}.{region_name or self.region_name}"
        client = boto3.client(  # type: ignore
            service_name,  # type: ignore
            region_name=region_name or self.region_name,
        )
        stubber = Stubber(client)  # type: ignore
        self._clients[key] = client  # type: ignore
        return client, stubber  # type: ignore

    def resource(self, service_name: str, **kwargs: Any) -> ServiceResource:
        """Return a stubbed resource."""
        kwargs.setdefault("region_name", self.region_name)
        resource: ServiceResource = boto3.resource(service_name, **kwargs)  # type: ignore
        resource.meta.client = self._clients[f"{service_name}.{kwargs['region_name']}"]
        return resource

    def service(self, service_name: str, region_name: Optional[str] = None) -> None:
        """Not implimented."""
        raise NotImplementedError


class MockCFNginContext(CfnginContext):
    """Subclass CFNgin context object for tests."""

    def __init__(
        self,
        *,
        config_path: Optional[Path] = None,
        config: Optional[CfnginConfig] = None,
        deploy_environment: Optional[DeployEnvironment] = None,
        parameters: Optional[MutableMapping[str, Any]] = None,
        force_stacks: Optional[List[str]] = None,
        region: Optional[str] = "us-east-1",
        stack_names: Optional[List[str]] = None,
        work_dir: Optional[Path] = None,
        **_: Any,
    ) -> None:
        """Instantiate class."""
        self._boto3_test_client = MutableMap()
        self._boto3_test_stubber = MutableMap()

        # used during init process
        self.s3_stubber = self.add_stubber("s3", region=region)

        super().__init__(
            config_path=config_path,
            config=config,
            deploy_environment=deploy_environment,
            force_stacks=force_stacks,
            parameters=parameters,
            stack_names=stack_names,
            work_dir=work_dir,
        )

    def add_stubber(self, service_name: str, region: Optional[str] = None) -> Stubber:
        """Add a stubber to context.

        Args:
            service_name: The name of a service, e.g. 's3' or 'ec2'.
            region: AWS region.

        """
        key = f"{service_name}.{region or self.env.aws_region}"

        self._boto3_test_client[key] = boto3.client(  # type: ignore
            service_name,  # type: ignore
            region_name=region or self.env.aws_region,
        )
        self._boto3_test_stubber[key] = Stubber(self._boto3_test_client[key])
        return self._boto3_test_stubber[key]

    def get_session(
        self,
        *,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_session_token: Optional[str] = None,
        profile: Optional[str] = None,
        region: Optional[str] = None,
    ) -> MockBoto3Session:
        """Wrap get_session to enable stubbing."""
        return MockBoto3Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
            clients=self._boto3_test_client,
            profile_name=profile,
            region_name=region or self.env.aws_region,
        )


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
        self.runway_version = SpecifierSet(">=1.10", prereleases=True)
        self.variables = MutableMap()

        # classmethods
        self.find_config_file = MagicMock(
            name="find_config_file", return_value="./runway.yml"
        )
        self.load_from_file = MagicMock(name="load_from_file", return_value=self)

    def __call__(self, **kwargs: Any) -> MockRunwayConfig:
        """Mock call to return self."""
        self._kwargs = kwargs
        return self


class MockRunwayContext(RunwayContext):
    """Subclass Runway context object for tests."""

    _use_concurrent: bool

    def __init__(
        self,
        *,
        command: Optional[RunwayActionTypeDef] = None,
        deploy_environment: Any = None,
        work_dir: Optional[Path] = None,
        **_: Any,
    ) -> None:
        """Instantiate class."""
        if not deploy_environment:
            deploy_environment = DeployEnvironment(environ={}, explicit_name="test")
        super().__init__(
            command=command, deploy_environment=deploy_environment, work_dir=work_dir
        )
        self._boto3_test_client = MutableMap()
        self._boto3_test_stubber = MutableMap()
        self._use_concurrent = True

    def add_stubber(self, service_name: str, region: Optional[str] = None) -> Stubber:
        """Add a stubber to context.

        Args:
            service_name: The name of a service, e.g. 's3' or 'ec2'.
            region: AWS region name.

        """
        key = f"{service_name}.{region or self.env.aws_region}"

        self._boto3_test_client[key] = boto3.client(  # type: ignore
            service_name,  # type: ignore
            region_name=region or self.env.aws_region,
            **self.boto3_credentials,
        )
        self._boto3_test_stubber[key] = Stubber(self._boto3_test_client[key])
        return self._boto3_test_stubber[key]

    def get_session(
        self,
        *,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_session_token: Optional[str] = None,
        profile: Optional[str] = None,
        region: Optional[str] = None,
    ) -> MockBoto3Session:
        """Wrap get_session to enable stubbing."""
        return MockBoto3Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
            clients=self._boto3_test_client,
            profile_name=profile,
            region_name=region or self.env.aws_region,
        )

    @property
    def use_concurrent(self) -> bool:  # pylint: disable=invalid-overridden-method
        """Override property of parent with something that can be set."""
        return self._use_concurrent

    @use_concurrent.setter  # type: ignore
    def use_concurrent(  # pylint: disable=invalid-overridden-method
        self, value: bool
    ) -> None:
        """Override property of parent with something that can be set.

        Args:
            value: New value for the attribute.

        """
        self._use_concurrent = value


class YamlLoader:
    """Load YAML files from a directory."""

    def __init__(
        self, root: Path, load_class: Optional[type] = None, load_type: str = "default"
    ) -> None:
        """Instantiate class.

        Args:
            root: Root directory.
            load_class: Class to use with load method.
            load_type: Contolls how content is passed to the load_class.

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
