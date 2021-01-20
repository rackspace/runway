"""Runway constants."""
from pathlib import Path

# A global credential cache that can be shared among boto3 sessions. This is
# inherently threadsafe thanks to the GIL:
# https://docs.python.org/3/glossary.html#term-global-interpreter-lock
BOTO3_CREDENTIAL_CACHE = {}

DOT_RUNWAY_DIR = Path.cwd() / ".runway"

DEFAULT_CACHE_DIR = DOT_RUNWAY_DIR / "cache"
