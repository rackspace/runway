"""Sample app."""
from aws_cdk import aws_iam as iam
from aws_cdk import core

from .hello_construct import HelloConstruct


class MyStack(core.Stack):  # pylint: disable=too-few-public-methods
    """My stack."""

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        """Instantiate class."""
        super().__init__(scope, id, **kwargs)

        hello = HelloConstruct(self, "MyHelloConstruct", num_buckets=1)
        user = iam.User(self, "MyUser")
        hello.grant_read(user)
