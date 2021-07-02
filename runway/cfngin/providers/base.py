"""Provider base class."""
# pylint: disable=no-self-use,unused-argument
from typing import Any, Optional


def not_implemented(method: str) -> None:
    """Wrap NotImplimentedError with a formatted message."""
    raise NotImplementedError(f"Provider does not support '{method}' method.")


class BaseProviderBuilder:
    """ProviderBuilder base class."""

    def build(self, region: Optional[str] = None) -> Any:
        """Abstract method."""
        not_implemented("build")


class BaseProvider:
    """Provider base class."""

    def get_stack(self, stack_name: str, *args: Any, **kwargs: Any) -> Any:
        """Abstract method."""
        not_implemented("get_stack")

    def get_outputs(self, stack_name: str, *args: Any, **kwargs: Any) -> Any:
        """Abstract method."""
        not_implemented("get_outputs")

    def get_output(self, stack: str, output: str) -> str:
        """Abstract method."""
        return self.get_outputs(stack)[output]


class Template:
    """CloudFormation stack template, which could be optionally uploaded to s3.

    Presence of the url attribute indicates that the template was uploaded to
    S3, and the uploaded template should be used for
    ``CreateStack``/``UpdateStack`` calls.

    """

    def __init__(self, url: Optional[str] = None, body: Optional[str] = None) -> None:
        """Instantiate class."""
        self.url = url
        self.body = body
