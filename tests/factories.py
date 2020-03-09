"""Test classes."""
import boto3
from botocore.stub import Stubber

from runway.util import MutableMap
from runway.context import Context as RunwayContext
from runway.cfngin.context import Context as CFNginContext


class MockBoto3Session(object):
    """Mock class that acts like a boto3.session.

    Must be preloaded with stubbers.

    """

    def __init__(self,
                 clients,
                 aws_access_key_id=None,
                 aws_secret_access_key=None,
                 aws_session_token=None,
                 profile_name=None,
                 region_name=None):
        """Instantiate class.

        Args:
            clients (Dict[str, Any]): Clients that have already been stubbed.
            aws_access_key_id (Optional[str]): Same as boto3.Session.
            aws_secret_access_key (Optional[str]): Same as boto3.Session.
            aws_session_token (Optional[str]): Same as boto3.Session.
            profile_name (Optional[str]): Same as boto3.Session.
            region_name (Optional[str]): Same as boto3.Session.

        """
        self._clients = clients
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_session_token = aws_session_token
        self.profile_name = profile_name
        self.region_name = region_name

    def client(self, service_name, region_name=None, **_):
        """Return a stubbed client.

        Args:
            service_name (str): The name of a service, e.g. 's3' or 'ec2'.

        Returns:
            Stubbed boto3 client.

        Raises:
            KeyError: Client was not stubbed from Context before trying to use.

        """
        key = '{}.{}'.format(service_name, region_name or self.region_name)
        return self._clients[key]

    def service(self, service_name, region_name=None):
        """Not implimented."""
        raise NotImplementedError


class MockCFNginContext(CFNginContext):
    """Subclass CFNgin context object for tests."""

    def __init__(self,
                 environment=None,
                 boto3_credentials=None,
                 stack_names=None,
                 config=None,
                 config_path=None,
                 region='us-east-1',
                 force_stacks=None):
        """Instantiate class."""
        if not boto3_credentials:
            boto3_credentials = {}

        self._boto3_test_client = MutableMap()
        self._boto3_test_stubber = MutableMap()

        # used during init process
        self.__boto3_credentials = boto3_credentials
        self.s3_stubber = self.add_stubber('s3', region=region)

        super(MockCFNginContext, self).__init__(environment=environment,
                                                boto3_credentials=boto3_credentials,
                                                stack_names=stack_names,
                                                config=config,
                                                config_path=config_path,
                                                region=region,
                                                force_stacks=force_stacks)

    def add_stubber(self, service_name, region=None):
        """Add a stubber to context.

        Args:
            service_name (str): The name of a service, e.g. 's3' or 'ec2'.

        """
        key = '{}.{}'.format(service_name, region or self.region)

        self._boto3_test_client[key] = boto3.client(
            service_name,
            region_name=region or self.region,
            **self.__boto3_credentials
        )
        self._boto3_test_stubber[key] = Stubber(
            self._boto3_test_client[key]
        )
        return self._boto3_test_stubber[key]

    def get_session(self, profile=None, region=None):
        """Wrap get_session to enable stubbing."""
        return MockBoto3Session(clients=self._boto3_test_client,
                                profile_name=profile,
                                region_name=region or self.region)


class MockRunwayContext(RunwayContext):
    """Subclass Runway context object for tests."""

    def __init__(self,
                 env_name,
                 env_region,
                 env_root,
                 env_vars=None,
                 command=None):
        """Instantiate class."""
        super(MockRunwayContext, self).__init__(env_name=env_name or 'test',
                                                env_region=env_region or 'us-east-1',
                                                env_root=env_root,
                                                env_vars=env_vars,
                                                command=command)
        self._boto3_test_client = MutableMap()
        self._boto3_test_stubber = MutableMap()

    def add_stubber(self, service_name, region=None):
        """Add a stubber to context.

        Args:
            service_name (str): The name of a service, e.g. 's3' or 'ec2'.

        """
        key = '{}.{}'.format(service_name, region or self.env_region)

        self._boto3_test_client[key] = boto3.client(
            service_name,
            region_name=region or self.env_region,
            **self.boto3_credentials
        )
        self._boto3_test_stubber[key] = Stubber(
            self._boto3_test_client[key]
        )
        return self._boto3_test_stubber[key]

    def get_session(self, profile=None, region=None):
        """Wrap get_session to enable stubbing."""
        return MockBoto3Session(clients=self._boto3_test_client,
                                profile_name=profile,
                                region_name=region or self.env_region)
