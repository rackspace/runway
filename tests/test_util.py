"""Tests for Runway utilities."""
import os.path
import string

from runway.util import load_object_from_string


def test_load_object_from_string():
    """Test load object from string."""
    tests = (
        ("string.Template", string.Template),
        ("os.path.basename", os.path.basename),
        ("string.ascii_letters", string.ascii_letters)
    )
    for test in tests:
        assert load_object_from_string(test[0]) is test[1]
