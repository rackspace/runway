"""Test runway.module.staticsite.handler."""
# pylint: disable=no-self-use
# pyright: basic
from __future__ import annotations

from typing import TYPE_CHECKING

from runway.module.staticsite.handler import StaticSite
from runway.module.staticsite.options.components import StaticSiteOptions
from runway.module.staticsite.parameters.models import (
    RunwayStaticSiteModuleParametersDataModel,
)

if TYPE_CHECKING:
    from pathlib import Path

    from runway.context import RunwayContext


class TestStaticSite:
    """Test StaticSite."""

    def test_init(self, runway_context: RunwayContext, tmp_path: Path) -> None:
        """Test init."""
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
