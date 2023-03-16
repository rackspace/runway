"""Test runway.core.utils."""

from __future__ import annotations

import pytest

from runway.utils import Version


class TestVersion:
    """Test Version."""

    @pytest.mark.parametrize(
        "version_str",
        [
            "1.2.3",
            "v1.2.3",
            "1.2.3a0",
            "1.2.3b4",
            "1.2.3rc4",
            "1.2.3.post4",
            "1.2.3b0.post4",
            "1.2.3.dev4",
            "1.2.3b0.dev4",
            "2021.10",
        ],
    )
    def test_pep_404(self, version_str: str) -> None:
        """Test with PEP 440 compliant versions."""
        obj = Version(version_str)
        assert str(obj) == version_str
        assert repr(obj) == f"<Version('{version_str.strip('v')}')>"

    @pytest.mark.parametrize(
        "pep_440, semver_str",
        [
            ("1.2.3", "1.2.3"),
            ("1.2.3", "v1.2.3"),
            ("1.2.3a0", "1.2.3-alpha"),
            ("1.2.3b4", "1.2.3-beta.4"),
            ("1.2.3rc4", "1.2.3-rc.4"),
            ("1.2.3.post4", "1.2.3-post.4"),
            ("1.2.3.dev4", "1.2.3-dev.4"),
        ],
    )
    def test_semver(self, pep_440: str, semver_str: str) -> None:
        """Test with SenVer compliant versions."""
        obj = Version(semver_str)
        assert str(obj) == semver_str
        assert repr(obj) == f"<Version('{pep_440}')>"
