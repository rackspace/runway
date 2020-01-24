"""Mock hook."""
# pylint: disable=unused-argument


def mock_hook(provider, context, **kwargs):
    """Mock hook.

    Returns:
        {'result': kwargs['value']}

    """
    return {'result': kwargs['value']}
