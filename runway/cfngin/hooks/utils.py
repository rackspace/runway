"""Hook utils."""
import os


def full_path(path):
    """Return full path."""
    return os.path.abspath(os.path.expanduser(path))
