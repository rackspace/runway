"""Test runway.module.cdk."""
# pylint: disable=no-self-use,unused-argument
# pyright: basic
from __future__ import annotations

from runway.config.models.runway.options.cdk import RunwayCdkModuleOptionsDataModel
from runway.module.cdk import CloudDevelopmentKitOptions


class TestCloudDevelopmentKitOptions:
    """Test CloudDevelopmentKitOptions."""

    def test_init(self) -> None:
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
