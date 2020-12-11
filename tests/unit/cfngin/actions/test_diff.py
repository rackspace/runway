"""Tests for runway.cfngin.actions.diff."""
# pylint: disable=no-self-use,protected-access
import logging
import unittest
from operator import attrgetter

import pytest
from botocore.exceptions import ClientError
from mock import MagicMock, patch

from runway.cfngin.actions.diff import (
    Action,
    DictValue,
    diff_dictionaries,
    diff_parameters,
)
from runway.cfngin.providers.aws.default import Provider
from runway.cfngin.status import SkippedStatus

from ..factories import MockProviderBuilder, MockThreadingEvent

MODULE = "runway.cfngin.actions.diff"


class TestAction(object):
    """Test runway.cfngin.actions.diff.Action."""

    @pytest.mark.parametrize(
        "bucket_name, forbidden, not_found",
        [
            ("test-bucket", False, True),
            ("test-bucket", True, False),
            (None, False, True),
            (None, True, False),
        ],
    )
    @patch(MODULE + ".Bucket", autospec=True)
    def test_pre_run(
        self,
        mock_bucket_init,
        caplog,
        bucket_name,
        forbidden,
        not_found,
        cfngin_context,
    ):
        """Test pre_run."""
        caplog.set_level(logging.DEBUG, logger=MODULE)
        mock_bucket = MagicMock()
        mock_bucket.name = bucket_name
        mock_bucket.forbidden = forbidden
        mock_bucket.not_found = not_found
        mock_bucket_init.return_value = mock_bucket
        cfngin_context.config.cfngin_bucket = bucket_name

        action = Action(cfngin_context)

        if forbidden and bucket_name:
            with pytest.raises(SystemExit) as excinfo:
                action.pre_run()
            assert excinfo.value.code == 1
            assert (
                "access denied for CFNgin bucket: %s" % bucket_name
            ) in caplog.messages
            return

        action.pre_run()

        if not_found and bucket_name:
            assert not action.bucket_name
            assert "proceeding without a cfngin_bucket..." in caplog.messages
            return

        assert action.bucket_name == bucket_name

    def test_diff_stack_validationerror_template_too_large(
        self, caplog, cfngin_context, monkeypatch
    ):
        """Test _diff_stack ValidationError - template too large."""
        caplog.set_level(logging.ERROR)

        cfngin_context.add_stubber("cloudformation")
        expected = SkippedStatus("cfngin_bucket: existing bucket required")
        provider = Provider(cfngin_context.get_session())
        mock_get_stack_changes = MagicMock(
            side_effect=ClientError(
                {
                    "Error": {
                        "Code": "ValidationError",
                        "Message": "length less than or equal to",
                    }
                },
                "create_change_set",
            )
        )
        monkeypatch.setattr(provider, "get_stack_changes", mock_get_stack_changes)
        stack = MagicMock()
        stack.region = cfngin_context.region
        stack.name = "test-stack"
        stack.fqn = "test-stack"
        stack.blueprint.rendered = "{}"
        stack.locked = False
        stack.status = None

        result = Action(
            context=cfngin_context,
            provider_builder=MockProviderBuilder(provider),
            cancel=MockThreadingEvent(),
        )._diff_stack(stack)
        mock_get_stack_changes.assert_called_once()
        assert result == expected


class TestDictValueFormat(unittest.TestCase):
    """Tests for runway.cfngin.actions.diff.DictValue."""

    def test_status(self):
        """Test status."""
        added = DictValue("k0", None, "value_0")
        self.assertEqual(added.status(), DictValue.ADDED)
        removed = DictValue("k1", "value_1", None)
        self.assertEqual(removed.status(), DictValue.REMOVED)
        modified = DictValue("k2", "value_1", "value_2")
        self.assertEqual(modified.status(), DictValue.MODIFIED)
        unmodified = DictValue("k3", "value_1", "value_1")
        self.assertEqual(unmodified.status(), DictValue.UNMODIFIED)

    def test_format(self):
        """Test format."""
        added = DictValue("k0", None, "value_0")
        self.assertEqual(added.changes(), ["+%s = %s" % (added.key, added.new_value)])
        removed = DictValue("k1", "value_1", None)
        self.assertEqual(
            removed.changes(), ["-%s = %s" % (removed.key, removed.old_value)]
        )
        modified = DictValue("k2", "value_1", "value_2")
        self.assertEqual(
            modified.changes(),
            [
                "-%s = %s" % (modified.key, modified.old_value),
                "+%s = %s" % (modified.key, modified.new_value),
            ],
        )
        unmodified = DictValue("k3", "value_1", "value_1")
        self.assertEqual(
            unmodified.changes(), [" %s = %s" % (unmodified.key, unmodified.old_value)]
        )
        self.assertEqual(
            unmodified.changes(), [" %s = %s" % (unmodified.key, unmodified.new_value)]
        )


class TestDiffDictionary(unittest.TestCase):
    """Tests for runway.cfngin.actions.diff.diff_dictionaries."""

    def test_diff_dictionaries(self):
        """Test diff dictionaries."""
        old_dict = {
            "a": "Apple",
            "b": "Banana",
            "c": "Corn",
        }
        new_dict = {
            "a": "Apple",
            "b": "Bob",
            "d": "Doug",
        }

        [count, changes] = diff_dictionaries(old_dict, new_dict)
        self.assertEqual(count, 3)
        expected_output = [
            DictValue("a", "Apple", "Apple"),
            DictValue("b", "Banana", "Bob"),
            DictValue("c", "Corn", None),
            DictValue("d", None, "Doug"),
        ]
        expected_output.sort(key=attrgetter("key"))

        # compare all the outputs to the expected change
        for expected_change in expected_output:
            change = changes.pop(0)
            self.assertEqual(change, expected_change)

        # No extra output
        self.assertEqual(len(changes), 0)


class TestDiffParameters(unittest.TestCase):
    """Tests for runway.cfngin.actions.diff.diff_parameters."""

    def test_diff_parameters_no_changes(self):
        """Test diff parameters no changes."""
        old_params = {"a": "Apple"}
        new_params = {"a": "Apple"}

        param_diffs = diff_parameters(old_params, new_params)
        self.assertEqual(param_diffs, [])
