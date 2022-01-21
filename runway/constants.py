"""Runway constants."""
from typing import Any, Dict

BOTO3_CREDENTIAL_CACHE: Dict[str, Any] = {}
"""A global credential cache that can be shared among boto3 sessions.
This is inherently threadsafe thanks to the GIL.
(https://docs.python.org/3/glossary.html#term-global-interpreter-lock)
"""
