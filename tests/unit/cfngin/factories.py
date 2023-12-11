"""Factories for tests."""
# pylint: disable=unused-argument
# pyright: basic
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, NamedTuple, Optional

from mock import MagicMock

from runway.cfngin.providers.aws.default import ProviderBuilder
from runway.config import CfnginConfig, CfnginStackDefinitionModel
from runway.context import CfnginContext

if TYPE_CHECKING:
    from runway.cfngin.providers.aws.default import Provider


class Lookup(NamedTuple):
    """Lookup named tuple."""

    type: str
    input: str
    raw: str


class MockThreadingEvent:
    """Mock thread events."""

    def wait(self, timeout: Optional[int] = None) -> bool:
        """Mock wait method."""
        return False


class MockProviderBuilder(ProviderBuilder):
    """Mock provider builder."""

    def __init__(  # pylint: disable=super-init-not-called
        self, *, provider: Provider, region: Optional[str] = None, **_: Any
    ) -> None:
        """Instantiate class."""
        self.provider = provider
        self.region = region

    def build(
        self, *, profile: Optional[str] = None, region: Optional[str] = None
    ) -> Provider:
        """Mock build method."""
        return self.provider


def mock_provider(**kwargs: Any) -> MagicMock:
    """Mock provider."""
    return MagicMock(**kwargs)


def mock_context(
    namespace: str = "default",
    extra_config_args: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> CfnginContext:
    """Mock context."""
    config_args = {"namespace": namespace}
    if extra_config_args:
        config_args.update(extra_config_args)
    config = CfnginConfig.parse_obj(config_args)
    if kwargs.get("environment"):
        return CfnginContext(config=config, **kwargs)
    return CfnginContext(config=config, environment={}, **kwargs)


def generate_definition(
    base_name: str, stack_id: Any = None, **overrides: Any
) -> CfnginStackDefinitionModel:
    """Generate definitions."""
    definition: Dict[str, Any] = {
        "name": f"{base_name}-{stack_id}" if stack_id else base_name,
        "class_path": f"tests.unit.cfngin.fixtures.mock_blueprints.{base_name.upper()}",
        "requires": [],
    }
    definition.update(overrides)
    return CfnginStackDefinitionModel(**definition)


def mock_lookup(
    lookup_input: Any, lookup_type: str, raw: Optional[str] = None
) -> Lookup:
    """Mock lookup."""
    if raw is None:
        raw = f"{lookup_type} {lookup_input}"
    return Lookup(type=lookup_type, input=lookup_input, raw=raw)


class SessionStub:
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

    def __init__(self, client_stub: Any):
        """Instantiate class."""
        self.client_stub = client_stub

    def client(self, region: str) -> Any:
        """Return the stubbed client object.

        Args:
            region: So boto3 won't complain

        Returns:
            The stubbed boto3 session

        """
        return self.client_stub
