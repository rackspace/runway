"""Provider base class."""
# pylint: disable=no-self-use,too-few-public-methods,unused-argument


def not_implemented(method):
    """Wrap NotImplimentedError with a formatted message."""
    raise NotImplementedError("Provider does not support '%s' method." % method)


class BaseProviderBuilder(object):
    """ProviderBuilder base class."""

    def build(self, region=None):
        """Abstract method."""
        not_implemented("build")


class BaseProvider(object):
    """Provider base class."""

    def get_stack(self, stack_name, *args, **kwargs):
        """Abstract method."""
        not_implemented("get_stack")

    def create_stack(self, *args, **kwargs):
        """Abstract method."""
        not_implemented("create_stack")

    def update_stack(self, *args, **kwargs):
        """Abstract method."""
        not_implemented("update_stack")

    def destroy_stack(self, stack, *args, **kwargs):
        """Abstract method."""
        not_implemented("destroy_stack")

    def get_stack_status(self, stack, *args, **kwargs):
        """Abstract method."""
        not_implemented("get_stack_status")

    def get_outputs(self, stack_name, *args, **kwargs):
        """Abstract method."""
        not_implemented("get_outputs")

    def get_output(self, stack, output):
        """Abstract method."""
        return self.get_outputs(stack)[output]


class Template(object):
    """CloudFormation stack template, which could be optionally uploaded to s3.

    Presence of the url attribute indicates that the template was uploaded to
    S3, and the uploaded template should be used for
    ``CreateStack``/``UpdateStack`` calls.

    """

    def __init__(self, url=None, body=None):
        """Instantiate class."""
        self.url = url
        self.body = body
