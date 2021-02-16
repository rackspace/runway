"""CFNgin lookups."""
# export resolve_lookups at this level
from .registry import register_lookup_handler, unregister_lookup_handler

__all__ = ["register_lookup_handler", "unregister_lookup_handler"]
