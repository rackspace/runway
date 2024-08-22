"""Provider base class."""

from __future__ import annotations

from typing import Any


def not_implemented(method: str) -> None:
    """Wrap NotImplimentedError with a formatted message."""
    raise NotImplementedError(f"Provider does not support '{method}' method.")


class BaseProviderBuilder:
    """ProviderBuilder base class."""

    def build(self, region: str | None = None) -> Any:  # noqa: ARG002
        """Abstract method."""
        not_implemented("build")


class BaseProvider:
    """Provider base class."""

    def get_stack(self, stack_name: str, *_args: Any, **_kwargs: Any) -> Any:  # noqa: ARG002
        """Abstract method."""
        not_implemented("get_stack")

    def get_outputs(self, stack_name: str, *_args: Any, **_kwargs: Any) -> Any:  # noqa: ARG002
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

    def __init__(self, url: str | None = None, body: str | None = None) -> None:
        """Instantiate class."""
        self.url = url
        self.body = body
