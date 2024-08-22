"""Runway constants."""

from __future__ import annotations

from typing import Any

BOTO3_CREDENTIAL_CACHE: dict[str, Any] = {}
"""A global credential cache that can be shared among boto3 sessions.
This is inherently threadsafe thanks to the GIL.
(https://docs.python.org/3/glossary.html#term-global-interpreter-lock)
"""
