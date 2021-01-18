"""Tests for the Source type object."""
# pylint: disable=no-self-use
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest

from runway.constants import DEFAULT_CACHE_DIR
from runway.sources.source import Source

if TYPE_CHECKING:
    from pathlib import Path

LOGGER = logging.getLogger("runway")


class TestSource:
    """Tests for the Source type object."""

    def test_fetch_not_implemented(self) -> None:
        """#fetch: By default a not implemented error should be thrown."""
        source = Source()
        with pytest.raises(NotImplementedError):
            source.fetch()

    def test_when_no_cache_dir_parameter_in_config(self) -> None:
        """The default when no cache_dir is passed in the config."""
        source = Source()
        assert source.cache_dir == DEFAULT_CACHE_DIR

    def test_a_cache_directory_is_created(self, cd_tmp_path: Path) -> None:
        """Ensure a cache directory is created."""
        source = Source(cache_dir=cd_tmp_path / ".runway" / "cache")
        assert source.cache_dir.is_dir()

    def test_directory_path_is_properly_sanitized(self) -> None:
        """Ensure that path values are sanitized for folder creation."""
        assert Source.sanitize_directory_path("foo@bar/baz:bop") == "foo_bar_baz_bop"
