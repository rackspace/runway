"""Test runway.module.cdk."""
# pylint: disable=no-self-use,unused-argument
# pyright: basic
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from runway.config.models.runway.options.cdk import RunwayCdkModuleOptionsDataModel
from runway.module.cdk import CloudDevelopmentKit, CloudDevelopmentKitOptions

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import LogCaptureFixture

    from runway.context import RunwayContext

MODULE = "runway.module.cdk"


class TestCloudDevelopmentKit:
    """Test CloudDevelopmentKit."""

    def test_init(
        self, caplog: LogCaptureFixture, runway_context: RunwayContext, tmp_path: Path
    ) -> None:
        """Test init."""
        caplog.set_level(logging.WARNING, logger=MODULE)
        obj = CloudDevelopmentKit(runway_context, module_root=tmp_path)
        assert not obj.init()
        assert (
            f"init not currently supported for {CloudDevelopmentKit.__name__}"
            in caplog.messages
        )


class TestCloudDevelopmentKitOptions:
    """Test CloudDevelopmentKitOptions."""

    def test___init__(self) -> None:
        """Test __init__."""
        data = RunwayCdkModuleOptionsDataModel(build_steps=["test"])
        obj = CloudDevelopmentKitOptions(data)
        assert obj.build_steps == data.build_steps
        assert obj.skip_npm_ci == data.skip_npm_ci

    def test_parse_obj(self) -> None:
        """Test parse_obj."""
        config = {"build_steps": ["test-cmd"], "skip_npm_ci": True, "key": "val"}
        obj = CloudDevelopmentKitOptions.parse_obj(config)
        assert isinstance(obj.data, RunwayCdkModuleOptionsDataModel)
        assert obj.data.build_steps == config["build_steps"]
        assert obj.data.skip_npm_ci == config["skip_npm_ci"]
        assert "key" not in obj.data.dict()
