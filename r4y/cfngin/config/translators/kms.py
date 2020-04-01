"""KMS translator.

.. important:: The translator is going to be deprecated in favor of the lookup.

"""
from ...lookups.handlers.kms import KmsLookup


def kms_simple_constructor(loader, node):
    """KMS simple constructor."""
    value = loader.construct_scalar(node)
    return KmsLookup.handle(value)
