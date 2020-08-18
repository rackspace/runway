"""Test classes."""
import io
import os
import sys

import boto3
import yaml
from botocore.stub import Stubber
from mock import MagicMock
from packaging.specifiers import SpecifierSet
from six import string_types

from runway.cfngin.context import Context as CFNginContext
from runway.config import DeploymentDefinition
from runway.context import Context as RunwayContext
from runway.core.components import DeployEnvironment
from runway.util import MutableMap


class MockBoto3Session(object):
    """Mock class that acts like a boto3.session.

    Must be preloaded with stubbers.

    """

    def __init__(
        self,
        clients=None,
        aws_access_key_id=None,
        aws_secret_access_key=None,
        aws_session_token=None,
        profile_name=None,
        region_name=None,
    ):
        """Instantiate class.

        Args:
            clients (Dict[str, Any]): Clients that have already been stubbed.
            aws_access_key_id (Optional[str]): Same as boto3.Session.
            aws_secret_access_key (Optional[str]): Same as boto3.Session.
            aws_session_token (Optional[str]): Same as boto3.Session.
            profile_name (Optional[str]): Same as boto3.Session.
            region_name (Optional[str]): Same as boto3.Session.

        """
        self._clients = clients or {}
        self._client_calls = {}
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_session_token = aws_session_token
        self.profile_name = profile_name
        self.region_name = region_name

    def assert_client_called_with(self, service_name, **kwargs):
        """Assert a client was created with the provided kwargs."""
        key = "{}.{}".format(service_name, kwargs.get("region_name", self.region_name))
        assert self._client_calls[key] == kwargs

    def client(self, service_name, **kwargs):
        """Return a stubbed client.

        Args:
            service_name (str): The name of a service, e.g. 's3' or 'ec2'.

        Returns:
            Stubbed boto3 client.

        Raises:
            KeyError: Client was not stubbed from Context before trying to use.

        """
        key = "{}.{}".format(service_name, kwargs.get("region_name", self.region_name))
        self._client_calls[key] = kwargs
        return self._clients[key]

    def register_client(self, service_name, region_name=None):
        """Register a client for the boto3 session.

        Args:
            service_name (str): The name of a service, e.g. 's3' or 'ec2'.
            region_name (Optional[str]): AWS region.

        """
        key = "{}.{}".format(service_name, region_name or self.region_name)
        client = boto3.client(service_name, region_name=region_name or self.region_name)
        stubber = Stubber(client)
        self._clients[key] = client
        return client, stubber

    def service(self, service_name, region_name=None):
        """Not implimented."""
        raise NotImplementedError


class MockCFNginContext(CFNginContext):
    """Subclass CFNgin context object for tests."""

    def __init__(
        self,
        environment=None,
        boto3_credentials=None,
        stack_names=None,
        config=None,
        config_path=None,
        region="us-east-1",
        force_stacks=None,
    ):
        """Instantiate class."""
        if not boto3_credentials:
            boto3_credentials = {}

        self._boto3_test_client = MutableMap()
        self._boto3_test_stubber = MutableMap()

        # used during init process
        self.__boto3_credentials = boto3_credentials
        self.s3_stubber = self.add_stubber("s3", region=region)

        super(MockCFNginContext, self).__init__(
            environment=environment,
            boto3_credentials=boto3_credentials,
            stack_names=stack_names,
            config=config,
            config_path=config_path,
            region=region,
            force_stacks=force_stacks,
        )

    def add_stubber(self, service_name, region=None):
        """Add a stubber to context.

        Args:
            service_name (str): The name of a service, e.g. 's3' or 'ec2'.
            region (Optional[str]): AWS region.

        """
        key = "{}.{}".format(service_name, region or self.region)

        self._boto3_test_client[key] = boto3.client(
            service_name, region_name=region or self.region, **self.__boto3_credentials
        )
        self._boto3_test_stubber[key] = Stubber(self._boto3_test_client[key])
        return self._boto3_test_stubber[key]

    def get_session(self, profile=None, region=None):
        """Wrap get_session to enable stubbing."""
        return MockBoto3Session(
            clients=self._boto3_test_client,
            profile_name=profile,
            region_name=region or self.region,
        )


# TODO use pytest-subprocess for when dropping python 2
class MockProcess(object):  # pylint: disable=too-few-public-methods
    """Instances of this class are the return_value of patched subprocess.Popen."""

    def __init__(self, returncode=0, stdout=None, universal_newlines=True):
        """Instantiate class.

        Args:
            returncode (int): Code that will be returned when the process exits.
            stdout (Optional[Union[bytes, str, List[str], Tuple(str, ...)]]): Content
                to be written accessable as stdout on the process.
            universal_newlines (bool): Use universal line endings.

        """
        self.returncode = returncode
        self.text_mode = bool(universal_newlines)
        self.stdout = self._prepare_buffer(stdout)

        self._wait = MagicMock(return_value=self.returncode)

    @property
    def wait(self):
        """Mock wait method as a property to call the stored MagicMock."""
        return self._wait

    def _prepare_buffer(self, data):
        """Prepare buffer for stdout/stderr.

        Args:
            data (Optional[Union[bytes, str, List[str], Tuple(str, ...)]]):
                Content to be written accessable as stdout on the process.

        Returns:
            Union[BytesIO, StringIO]

        """
        result = None
        linesep = os.linesep

        if isinstance(data, (list, tuple)):
            result = linesep.join(data)

        if isinstance(data, string_types):
            result = data

        if result:
            if not result.endswith(linesep):
                result += linesep
            if self.text_mode:
                result.replace("\r\n", "\n")

        io_base = io.StringIO() if self.text_mode else io.BytesIO()

        if result:
            if sys.version_info.major < 3:
                io_base.write(result.decode("UTF-8"))
            else:
                io_base.write(result)
            io_base.seek(0)  # return to the begining of the stream
        return io_base


class MockRunwayConfig(MutableMap):
    """Mock Runway config object."""

    def __init__(self, **kwargs):
        """Instantiate class."""
        super(MockRunwayConfig, self).__init__()
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

    def __call__(self, **kwargs):
        """Mock call to return self."""
        self._kwargs = kwargs
        return self


class MockRunwayContext(RunwayContext):
    """Subclass Runway context object for tests."""

    def __init__(self, command=None, deploy_environment=None):
        """Instantiate class."""
        if not deploy_environment:
            deploy_environment = DeployEnvironment(environ={}, explicit_name="test")
        super(MockRunwayContext, self).__init__(
            command=command, deploy_environment=deploy_environment
        )
        self._boto3_test_client = MutableMap()
        self._boto3_test_stubber = MutableMap()
        self._use_concurrent = True

    def add_stubber(self, service_name, region=None):
        """Add a stubber to context.

        Args:
            service_name (str): The name of a service, e.g. 's3' or 'ec2'.
            region (Optional[str]): AWS region name.

        """
        key = "{}.{}".format(service_name, region or self.env_region)

        self._boto3_test_client[key] = boto3.client(
            service_name,
            region_name=region or self.env_region,
            **self.boto3_credentials
        )
        self._boto3_test_stubber[key] = Stubber(self._boto3_test_client[key])
        return self._boto3_test_stubber[key]

    def get_session(self, profile=None, region=None):
        """Wrap get_session to enable stubbing."""
        return MockBoto3Session(
            clients=self._boto3_test_client,
            profile_name=profile,
            region_name=region or self.env_region,
        )

    @property
    def use_concurrent(self):
        """Override property of parent with something that can be set."""
        return self._use_concurrent

    @use_concurrent.setter
    def use_concurrent(self, value):
        """Override property of parent with something that can be set.

        Args:
            value (bool): New value for the attribute.

        """
        self._use_concurrent = value


class YamlLoader(object):
    """Load YAML files from a directory."""

    def __init__(self, root, load_class=None, load_type="default"):
        """Instantiate class.

        Args:
            root (Path): Root directory.
            load_class (Any): Class to use with load method.
            load_type (str): Contolls how content is passed to the load_class.

        """
        self.load_class = load_class
        self.load_type = load_type
        root.absolute()
        self.root = root

    def get(self, file_name):
        """Get raw YAML file contents.

        Args:
            file_name (str): Name of the file to load.

        Returns:
            Dict[str, Any]: Content of the file loaded by PyYAML.

        """
        if not file_name.endswith(".yml") or not file_name.endswith(".yaml"):
            file_name += ".yml"
        if sys.version_info.major > 2:
            content = (self.root / file_name).read_text()
        else:
            content = (self.root / file_name).read_text().decode()
        return yaml.safe_load(content)

    def load(self, file_name):
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
        raise ValueError('invalid load_type; "{}"'.format(self.load_type))


class YamlLoaderDeploymet(YamlLoader):
    """Load deployment YAML files from a directory."""

    def __init__(self, root):
        """Instantiate class.

        Args:
            root (Path): Root directory.

        """
        super(YamlLoaderDeploymet, self).__init__(root, load_class=DeploymentDefinition)

    def load(self, file_name):
        """Load YAML file contents.

        Args:
            file_name (str): Name of the file to load.

        Returns:
            DeploymentDefinition

        """
        return self.load_class.from_list([self.get(file_name)])[0]
