"""Sync strategies.

.. Derived from software distributed by Amazon.com, Inc - http://aws.amazon.com/apache2.0/
   https://github.com/aws/aws-cli/blob/83b43782dd/awscli/customizations/s3/syncstrategy/__init__.py

"""
from .base import BaseSync, MissingFileSync, NeverSync, SizeAndLastModifiedSync
from .delete import DeleteSync
from .exact_timestamps import ExactTimestampsSync
from .register import register_sync_strategies
from .size_only import SizeOnlySync

__all__ = [
    "BaseSync",
    "DeleteSync",
    "ExactTimestampsSync",
    "MissingFileSync",
    "NeverSync",
    "register_sync_strategies",
    "SizeAndLastModifiedSync",
    "SizeOnlySync",
]
