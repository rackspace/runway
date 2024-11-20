"""Test runway.exceptions."""

from __future__ import annotations

import pickle
from typing import TYPE_CHECKING

from runway.exceptions import ConfigNotFound

if TYPE_CHECKING:
    from pathlib import Path

class TestConfigNotFound:
    """Test "ConfigNotFound."""

    def test_pickle(self, tmp_path: Path) -> None:
        """Test pickling."""
        exc = ConfigNotFound(["foo"], tmp_path)
        assert str(pickle.loads(pickle.dumps(exc))) == str(exc)
