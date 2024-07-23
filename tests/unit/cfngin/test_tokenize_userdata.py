"""Tests for runway.cfngin.tokenize_userdata."""

# pyright: basic
import unittest

import yaml

from runway.cfngin.tokenize_userdata import cf_tokenize


class TestCfTokenize(unittest.TestCase):
    """Tests for runway.cfngin.tokenize_userdata."""

    def test_tokenize(self) -> None:
        """Test tokenize."""
        user_data = ["field0", 'Ref("SshKey")', "field1", 'Fn::GetAtt("Blah", "Woot")']
        user_data_dump = yaml.dump(user_data)
        parts = cf_tokenize(user_data_dump)
        assert isinstance(parts[1], dict)
        assert isinstance(parts[3], dict)
        assert parts[1]["Ref"] == "SshKey"  # type: ignore
        assert parts[3]["Fn::GetAtt"] == ["Blah", "Woot"]  # type: ignore
        assert len(parts) == 5
