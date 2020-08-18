"""Sample app."""
from aws_cdk import aws_sns as sns
from aws_cdk import core


class MyStack2(core.Stack):  # pylint: disable=too-few-public-methods
    """My stack."""

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        """Instantiate class."""
        super().__init__(scope, id, **kwargs)

        sns.Topic(self, "MySecondTopic", display_name="My Second Topic")
