"""Sample app."""
from aws_cdk import aws_iam as iam
from aws_cdk import aws_s3 as s3
from aws_cdk import core


class HelloConstruct(core.Construct):
    """Hello construct."""

    @property
    def buckets(self):
        """Return a tuple of buckets."""
        return tuple(self._buckets)

    def __init__(self, scope: core.Construct, id: str, num_buckets: int) -> None:
        """Instantiate class."""
        super().__init__(scope, id)
        self._buckets = []
        for i in range(0, num_buckets):
            self._buckets.append(s3.Bucket(self, f"Bucket-{i}"))

    def grant_read(self, principal: iam.IPrincipal):
        """Grant reed access."""
        for b in self.buckets:
            b.grant_read(principal, "*")
