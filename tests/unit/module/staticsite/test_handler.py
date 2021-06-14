"""Test runway.module.staticsite.handler."""
# pylint: disable=no-self-use
# pyright: basic
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from runway.module.staticsite.handler import StaticSite
from runway.module.staticsite.options.components import StaticSiteOptions
from runway.module.staticsite.parameters.models import (
    RunwayStaticSiteModuleParametersDataModel,
)

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import LogCaptureFixture

    from runway.context import RunwayContext


MODULE = "runway.module.staticsite.handler"


class TestStaticSite:
    """Test StaticSite."""

    def test___init__(self, runway_context: RunwayContext, tmp_path: Path) -> None:
        """Test __init__."""
        obj = StaticSite(
            runway_context,
            module_root=tmp_path,
            options={"build_output": "./dist"},
            parameters={"namespace": "test"},
        )
        assert obj.ctx == runway_context
        assert isinstance(obj.options, StaticSiteOptions)
        assert obj.options == StaticSiteOptions.parse_obj({"build_output": "./dist"})
        assert isinstance(obj.parameters, RunwayStaticSiteModuleParametersDataModel)
        assert obj.parameters == RunwayStaticSiteModuleParametersDataModel.parse_obj(
            {"namespace": "test"}
        )
        assert obj.path == tmp_path

    def test_init(
        self, caplog: LogCaptureFixture, runway_context: RunwayContext, tmp_path: Path
    ) -> None:
        """Test init."""
        caplog.set_level(logging.WARNING, logger=MODULE)
        obj = StaticSite(
            runway_context, module_root=tmp_path, parameters={"namespace": "test"}
        )
        assert not obj.init()
        assert (
            f"init not currently supported for {StaticSite.__name__}" in caplog.messages
        )
