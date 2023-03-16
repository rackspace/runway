"""Tests for runway.cfngin.lookups.handlers.rxref."""
# pylint: disable=protected-access
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from mock import Mock

from runway._logging import LogLevels
from runway.cfngin.lookups.handlers.rxref import RxrefLookup

if TYPE_CHECKING:
    from pytest import LogCaptureFixture
    from pytest_mock import MockerFixture

    from ....factories import MockCFNginContext

MODULE = "runway.cfngin.lookups.handlers.rxref"


class TestRxrefLookup:
    """Tests for runway.cfngin.lookups.handlers.rxref.RxrefLookup."""

    @pytest.mark.parametrize(
        "provided, expected",
        [
            ("stack-name::Output", "namespace-stack-name.Output"),
            ("stack-name.Output", "namespace-stack-name.Output"),
            (
                "stack-name.Output::default=bar",
                "namespace-stack-name.Output::default=bar",
            ),
        ],
    )
    def test_handle(
        self,
        cfngin_context: MockCFNginContext,
        expected: str,
        mocker: MockerFixture,
        provided: str,
    ) -> None:
        """Test handle."""
        cfngin_context.config.namespace = "namespace"
        cfn = mocker.patch(f"{MODULE}.CfnLookup")
        cfn.handle.return_value = "success"
        provider = Mock(name="provider")
        assert RxrefLookup.handle(provided, context=cfngin_context, provider=provider)
        cfn.handle.assert_called_once_with(
            expected, context=cfngin_context, provider=provider
        )

    def test_legacy_parse(
        self, caplog: LogCaptureFixture, mocker: MockerFixture
    ) -> None:
        """Test legacy_parse."""
        query = "foo"
        caplog.set_level(LogLevels.WARNING, MODULE)
        deconstruct = mocker.patch(f"{MODULE}.deconstruct", return_value="success")
        assert RxrefLookup.legacy_parse(query) == (deconstruct.return_value, {})
        deconstruct.assert_called_once_with(query)
        assert f"${{rxref {query}}}: {RxrefLookup.DEPRECATION_MSG}" in caplog.messages
