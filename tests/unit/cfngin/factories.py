"""Factories for tests."""
# pylint: disable=no-self-use,unused-argument
from collections import namedtuple

from mock import MagicMock

from runway.cfngin.config import Config, Stack
from runway.cfngin.context import Context

Lookup = namedtuple("Lookup", ("type", "input", "raw"))


class MockThreadingEvent(object):  # pylint: disable=too-few-public-methods
    """Mock thread events."""

    def wait(self, timeout=None):
        """Mock wait method."""
        return False


class MockProviderBuilder(object):  # pylint: disable=too-few-public-methods
    """Mock provider builder."""

    def __init__(self, provider, region=None):
        """Instantiate class."""
        self.provider = provider
        self.region = region

    def build(self, region=None, profile=None):
        """Mock build method."""
        return self.provider


def mock_provider(**kwargs):
    """Mock provider."""
    return MagicMock(**kwargs)


def mock_context(namespace="default", extra_config_args=None, **kwargs):
    """Mock context."""
    config_args = {"namespace": namespace}
    if extra_config_args:
        config_args.update(extra_config_args)
    config = Config(config_args)
    if kwargs.get("environment"):
        return Context(config=config, **kwargs)
    return Context(config=config, environment={}, **kwargs)


def generate_definition(base_name, stack_id, **overrides):
    """Generate definitions."""
    definition = {
        "name": "%s.%d" % (base_name, stack_id),
        "class_path": "tests.unit.cfngin.fixtures.mock_blueprints.%s"
        % (base_name.upper()),
        "requires": [],
    }
    definition.update(overrides)
    return Stack(definition)


def mock_lookup(lookup_input, lookup_type, raw=None):
    """Mock lookup."""
    if raw is None:
        raw = "%s %s" % (lookup_type, lookup_input)
    return Lookup(type=lookup_type, input=lookup_input, raw=raw)


class SessionStub(object):  # pylint: disable=too-few-public-methods
    """Stubber class for boto3 sessions made with session_cache.get_session().

    This is a helper class that should be used when trying to stub out
    get_session() calls using the boto3.stubber.

    Example Usage:

        @mock.patch('runway.cfngin.lookups.handlers.myfile.get_session',
                return_value=sessionStub(client))
        def myfile_test(self, client_stub):
            ...

    Attributes:
        client_stub (:class:`boto3.session.Session`:): boto3 session stub

    """

    def __init__(self, client_stub):
        """Instantiate class."""
        self.client_stub = client_stub

    def client(self, region):
        """Return the stubbed client object.

        Args:
            region (str): So boto3 won't complain

        Returns:
            :class:`boto3.session.Session`: The stubbed boto3 session

        """
        return self.client_stub
